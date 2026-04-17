import logging
import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CustomUser, RestorePasswordRecord
from .utils import validate_and_change_password, check_old_password
from .verification.email_send import send_email
from .verification.sms_send import (
    get_phone_number, sms_code_gen, sms_sending,
    SMS_TEXT, SMS_TRAFFIC_LOGIN, SMS_TRAFFIC_PASS,
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user(request):
    """Check whether the requesting user has a Steam ID linked."""
    steam_id = request.user.steam_id
    return Response({'success': bool(steam_id)})


@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
def sms_send(request):
    """Send SMS verification code to the requesting user's phone number."""
    try:
        phone_number = get_phone_number(request.data.get('phone_number'))
        user = request.user
        user.phone_number = phone_number
        sms_code = sms_code_gen(5)
        user.verfication_code = sms_code
        user.save()

        response = sms_sending(phone_number, sms_code, SMS_TEXT, SMS_TRAFFIC_LOGIN, SMS_TRAFFIC_PASS)
        if response.status_code != 200:
            return Response({'error': 'SMS send failed.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)
    except Exception as exc:
        logger.exception('sms_send failed')
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_sms_code(request):
    """Verify SMS OTP for the requesting user."""
    sms_code = request.data.get('sms_code')
    user = request.user

    if user.verfication_code is None:
        return Response({'error': 'No verification code issued.'}, status=status.HTTP_400_BAD_REQUEST)

    if str(user.verfication_code) == str(sms_code):
        user.verified_phone = True
        user.save()
        return Response(status=status.HTTP_200_OK)

    return Response({'error': 'Incorrect SMS code.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def restore_password(request):
    """Send a password-reset link to the given email."""
    request_email = request.data.get('email', '')
    try:
        user = CustomUser.objects.get(email=request_email)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)

    restore_record = RestorePasswordRecord.objects.create(user=user)
    restore_link = f'{settings.FRONTEND_HOST}/recovery?token={restore_record.token}'
    send_email(
        email=user.email,
        message=f'Для восстановления пароля перейдите {restore_link}',
        tittle='Восстановление пароля',
    )
    return Response(status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def restore_password_submit(request):
    """Validate reset token (GET) or apply new password (POST)."""
    token = request.GET.get('token')
    try:
        restore_record = RestorePasswordRecord.objects.get(token=token, used=False)
    except RestorePasswordRecord.DoesNotExist:
        return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(status=status.HTTP_200_OK)

    new_password = request.data.get('password', '')
    new_password_copy = request.data.get('password_copy', '')
    user = get_user_model().objects.get(email=restore_record.user.email)
    validate_and_change_password(new_password, new_password_copy, user=user)
    restore_record.used = True
    restore_record.save()
    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change password for the authenticated user."""
    old_password = request.data.get('old_password', '')
    new_password = request.data.get('new_password', '')
    new_password_copy = request.data.get('new_password_copy', '')
    user = request.user
    check_old_password(user, password=old_password)
    validate_and_change_password(new_password, new_password_copy, user=user)
    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_id(request):
    return Response({'user_id': request.user.id, 'username': request.user.username})
