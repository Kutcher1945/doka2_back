import base64
import hashlib
import json
import logging

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from payments.monetix.utils import get_user_wallet
from .models import UserVerification, VerificationHistory
from .utils import get_user_verification, generate_verification_id

logger = logging.getLogger(__name__)

SHUFTIPRO_URL_STATUS = 'https://api.shuftipro.com/status'
SHUFTIPRO_URL = 'https://api.shuftipro.com'


def _shuftipro_auth_header() -> str:
    auth = '{}:{}'.format(settings.SHUFTIPRO_CLIENT_ID, settings.SHUFTIPRO_SECRET_KEY)
    return base64.b64encode(auth.encode()).decode()


def _verify_shuftipro_signature(response_body: bytes, sp_signature: str) -> bool:
    """Verify that the response body was signed by ShuftiPro using their secret key."""
    hashed_secret = hashlib.sha256(settings.SHUFTIPRO_SECRET_KEY.encode()).hexdigest()
    calculated = hashlib.sha256(
        '{}{}'.format(response_body.decode(), hashed_secret).encode()
    ).hexdigest()
    return sp_signature == calculated


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_verification_url(request):
    """Generate a ShuftiPro verification URL for the requesting user."""
    user = request.user
    user_verification = get_user_verification(user)

    if user_verification.is_verified:
        return Response({'error': 'User is already verified.'}, status=status.HTTP_409_CONFLICT)

    verification_id = generate_verification_id(user.id)

    VerificationHistory.objects.create(
        user_verification=user_verification,
        verification_id=verification_id,
    )

    verification_request = {
        'reference': str(verification_id),
        'callback_url': f'{settings.BACKEND_HOST}/auth/verification/verification_callback/',
        'email': str(user.email),
        'country': '',
        'language': 'RU',
        'redirect_url': f'{settings.FRONTEND_HOST}/cabinet/profile?verificated=true&verification_id={verification_id}/',
        'verification_mode': 'image_only',
        'allow_offline': '1',
        'allow_online': '1',
        'show_privacy_policy': '1',
        'show_results': '1',
        'show_consent': '1',
        'show_feedback_form': '0',
        'face': {},
        'document': {
            'name': '', 'dob': '', 'gender': '', 'place_of_issue': '',
            'document_number': '', 'expiry_date': '', 'issue_date': '',
            'allow_offline': '1', 'allow_online': '1', 'fetch_enhanced_data': '1',
            'supported_types': ['id_card', 'passport'],
        },
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Basic {_shuftipro_auth_header()}',
    }

    response = requests.post(SHUFTIPRO_URL, headers=headers, data=json.dumps(verification_request))

    sp_signature = response.headers.get('Signature', '')
    if not _verify_shuftipro_signature(response.content, sp_signature):
        logger.error('ShuftiPro signature mismatch on generate_verification_url')
        return Response({'error': 'Invalid signature from ShuftiPro.'}, status=status.HTTP_502_BAD_GATEWAY)

    json_response = json.loads(response.content)
    logger.info('ShuftiPro event: %s for user %s', json_response.get('event'), user.id)

    if json_response.get('event') == 'request.pending':
        return Response({'url': json_response['verification_url']})

    return Response({'error': 'Unexpected ShuftiPro response.', 'event': json_response.get('event')},
                    status=status.HTTP_409_CONFLICT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_verification_data(request):
    """Check current verification status for the requesting user."""
    user_verification = get_user_verification(request.user)
    latest = VerificationHistory.objects.filter(
        user_verification=user_verification
    ).order_by('-verification_time').first()

    if not latest:
        return Response({'error': 'No verification attempt found.'}, status=status.HTTP_404_NOT_FOUND)

    status_request = {'reference': str(latest.verification_id)}
    b64 = _shuftipro_auth_header()

    response = requests.post(
        SHUFTIPRO_URL_STATUS,
        headers={'Authorization': f'Basic {b64}', 'Content-Type': 'application/json'},
        data=json.dumps(status_request),
    )

    sp_signature = response.headers.get('Signature', '')
    # For status endpoint ShuftiPro uses raw secret (not hashed) for signature
    calculated = hashlib.sha256(
        '{}{}'.format(response.content.decode(), settings.SHUFTIPRO_SECRET_KEY).encode()
    ).hexdigest()

    if sp_signature != calculated:
        logger.error('ShuftiPro signature mismatch on get_verification_data')
        return Response({'error': 'Invalid signature from ShuftiPro.'}, status=status.HTTP_502_BAD_GATEWAY)

    json_response = json.loads(response.content)
    logger.info('ShuftiPro status response: %s', json_response.get('event'))
    return Response({'event': json_response.get('event')})


@api_view(['POST'])
@permission_classes([AllowAny])
def verification_callback(request):
    """
    Webhook called by ShuftiPro when verification completes.
    Must remain AllowAny (external webhook), but we verify the ShuftiPro
    signature BEFORE trusting any payload data.
    """
    body = request.body
    sp_signature = request.headers.get('Signature', '')

    # Verify signature first — reject anything that doesn't come from ShuftiPro
    hashed_secret = hashlib.sha256(settings.SHUFTIPRO_SECRET_KEY.encode()).hexdigest()
    calculated = hashlib.sha256(
        '{}{}'.format(body.decode(), hashed_secret).encode()
    ).hexdigest()

    if sp_signature != calculated:
        logger.warning('verification_callback: invalid signature, ignoring request')
        return Response(status=status.HTTP_400_BAD_REQUEST)

    logger.info('verification_callback body: %s', body.decode())

    try:
        json_data = json.loads(body.decode())

        if json_data['event'] != 'verification.accepted':
            return Response(status=status.HTTP_200_OK)

        doc_data = json_data['verification_data']['document']
        individual_id = doc_data['document_number']

        if UserVerification.objects.filter(individual_identification_number=individual_id).exists():
            return Response(
                {'error': 'Individual Identification Number already exists.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        verification_history = VerificationHistory.objects.get(verification_id=json_data['reference'])
        verification_history.status = json_data['event']

        user_verification = verification_history.user_verification
        user_verification.first_name = doc_data['name']['first_name']
        user_verification.last_name = doc_data['name']['last_name']
        user_verification.date_of_birth = doc_data['dob']
        user_verification.individual_identification_number = doc_data['document_number']
        user_verification.gender = doc_data['gender']
        user_verification.face_match_confidence = json_data['verification_result']['face']
        user_verification.document_number = json_data['additional_data']['document']['proof']['document_number']
        user_verification.country_code = doc_data['country']
        user_verification.is_verified = True

        country_currency_map = {
            'KZ': ('KZT', 'kk'),
            'UA': ('UAH', 'ua'),
            'UZ': ('UZS', 'uz'),
            'RU': ('RUB', 'ru'),
        }
        user_wallet = get_user_wallet(user_verification.user)
        currency, language = country_currency_map.get(doc_data['country'], (user_wallet.currency, user_wallet.language_payments))
        user_wallet.currency = currency
        user_wallet.language_payments = language
        user_wallet.save()

        user_verification.user.verification = user_verification
        user_verification.user.save()
        verification_history.save()
        user_verification.save()

    except Exception:
        logger.exception('verification_callback processing failed')
        return Response({'error': 'Processing failed.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(status=status.HTTP_200_OK)
