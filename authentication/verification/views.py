import base64
import hashlib
import json

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from payments.monetix.utils import get_user_wallet
from .models import *
from .utils import *

SHUFTIPRO_URL_STATUS = 'https://api.shuftipro.com/status'
SHUFTIPRO_URL = 'https://api.shuftipro.com'


@api_view(['GET'])
@permission_classes([AllowAny])
def generate_verification_url(request):
    """Generate verification url and send it to front..."""

    user_id = request.GET.get('user_id')

    user = CustomUser.objects.get(id=user_id)

    user_verification = get_user_verification(user)
    if user_verification.is_verified:
        return Response({"text": "User is verified"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    verification_id = generate_verification_id(user_id)
    custom_user = CustomUser.objects.get(id=user_id)

    user_verification = get_user_verification(custom_user)

    VerificationHistory.objects.create(
        user_verification=user_verification,
        verification_id=verification_id,
    )

    verification_request = {
        # your unique request reference
        "reference": str(verification_id),
        # URL where you will receive the webhooks from Shufti Pro
        'callback_url': f'{settings.BACKEND_HOST}/auth/verification/verification_callback/',
        # end-user email
        "email": str(custom_user.email),
        # end-user country
        "country": "",
        # select ISO2 Code for your desired language on verification screen
        "language": "RU",
        # URL where end-user will be redirected after verification completed
        "redirect_url": f'{settings.FRONTEND_HOST}/cabinet/profile?verificated=true&verification_id={verification_id}/',
        # what kind of proofs will be provided to Shufti Pro for verification?
        "verification_mode": "image_only",
        # allow end-user to upload verification proofs if the webcam is not accessible
        "allow_offline": "1",
        # allow end-user to upload real-time or already catured proofs
        "allow_online": "1",
        # privacy policy screen will be shown to end-user
        "show_privacy_policy": "1",
        # verification results screen will be shown to end-user
        "show_results": "1",
        # consent screen will be shown to end-user
        "show_consent": "1",
        # User cannot send Feedback
        "show_feedback_form": "0",
    }
    # face onsite verification
    verification_request['face'] = {}
    # document onsite verification with OCR
    verification_request['document'] = {
        'name': "",
        'dob': "",
        'gender': "",
        'place_of_issue': "",
        'document_number': "",
        'expiry_date': "",
        'issue_date': "",
        'allow_offline': '1',
        'allow_online': '1',
        'fetch_enhanced_data': "1",
        'supported_types': ['id_card', 'passport'],
    }

    # Calling Shufti Pro request API using python  requests
    auth = '{}:{}'.format(SHUFTIPRO_CLIENT_ID, SHUFTIPRO_SECRET_KEY)
    b64Val = base64.b64encode(auth.encode()).decode()
    print("json.dumps(verification_request) %s " % json.dumps(verification_request))

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {b64Val}"  # if access token then replace "Basic" with "Bearer"
    }

    response = requests.post(SHUFTIPRO_URL,
                             headers=headers,
                             data=json.dumps(verification_request))

    # get Shufti Pro Signature
    sp_signature = response.headers.get('Signature')

    # convert secret key into sha256
    hashed_secret_key = hashlib.sha256(SHUFTIPRO_SECRET_KEY.encode()).hexdigest()

    # calculating signature for verification
    calculated_signature = hashlib.sha256('{}{}'.format(
        response.content.decode(), hashed_secret_key).encode()).hexdigest()
    # Convert json string to json object
    json_response = json.loads(response.content)

    # Get event returned
    event_name = json_response['event']
    if event_name == 'request.pending':
        if sp_signature == calculated_signature:
            verification_url = json_response['verification_url']
            return Response({"url": verification_url}, status=status.HTTP_200_OK)

        else:
            return Response({"text": response.content}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"text": response.content}, status=status.HTTP_409_CONFLICT)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_verification_data(request):
    """Get verification data from ShuftiPro by verification id"""

    verification_id = request.GET.get('verification_id')

    status_request = {
        "reference": str(verification_id)
    }

    # Calling Shufti Pro request API using python requests
    auth = '{}:{}'.format(SHUFTIPRO_CLIENT_ID, SHUFTIPRO_SECRET_KEY)
    b64Val = base64.b64encode(auth.encode()).decode()

    response = requests.post(SHUFTIPRO_URL_STATUS,
                             headers={"Authorization": "Basic %s" % b64Val, "Content-Type": "application/json"},
                             data=json.dumps(status_request))

    # Calculating signature for verification
    # calculated signature functionality cannot be implement in case of access token
    calculated_signature = hashlib.sha256(
        '{}{}'.format(response.content.decode(), SHUFTIPRO_SECRET_KEY).encode()).hexdigest()

    # Convert json string to json object
    json_response = json.loads(response.content)
    sp_signature = response.headers.get('Signature', '')

    if sp_signature == calculated_signature:
        print('Response : {}'.format(json_response))
        event = json_response['event']
        if event == "verification.accepted":
            return Response({"response": event}, status=status.HTTP_200_OK)
        else:
            return Response({"response": event}, status=status.HTTP_200_OK)
    else:
        print('Invalid Signature: {}'.format(json_response))

    return Response({"response": json_response}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verification_callback(request):
    print("request.body : %s " % request.body.decode())
    json_data = json.loads(request.body.decode())

    try:
        if json_data['event'] == 'verification.accepted':
            individual_identification_number = json_data['verification_data']['document']['document_number']
            if UserVerification.objects.filter(individual_identification_number=individual_identification_number).exists():
                return Response(data={"error": "Individual Identification Number already exists"},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)

            verification_history = VerificationHistory.objects.get(verification_id=json_data['reference'])

            verification_history.status = json_data['event']
            user_verification = verification_history.user_verification
            document_country_code = json_data['verification_data']['document']['country']

            user_verification.first_name = json_data['verification_data']['document']['name']['first_name']
            user_verification.last_name = json_data['verification_data']['document']['name']['last_name']
            user_verification.date_of_birth = json_data['verification_data']['document']['dob']
            user_verification.individual_identification_number = json_data['verification_data']['document'][
                'document_number']
            user_verification.gender = json_data['verification_data']['document']['gender']
            user_verification.face_match_confidence = json_data['verification_result']['face']
            user_verification.document_number = json_data['additional_data']['document']['proof']['document_number']
            user_verification.country_code = document_country_code
            user_verification.is_verified = True

            user_wallet = get_user_wallet(user_verification.user)

            if document_country_code == "KZ":
                user_wallet.currency = "KZT"
                user_wallet.language_payments = "kk"
            elif document_country_code == "UA":
                user_wallet.currency = "UAH"
                user_wallet.language_payments = "ua"
            elif document_country_code == "UZ":
                user_wallet.currency = "UZS"
                user_wallet.language_payments = "uz"
            elif document_country_code == "RU":
                user_wallet.currency = "RUB"
                user_wallet.language_payments = "ru"

            user_wallet.save()

            user_verification.user.verification = user_verification
            user_verification.user.save()
            verification_history.save()
            user_verification.save()
    except Exception as exception:
        print("exception: %s " % exception)
        return Response("Exception: %s" % exception, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(status=status.HTTP_200_OK)

