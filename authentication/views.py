import json

from authentication.models import CustomUser
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http.response import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CustomUser
from .models import RestorePasswordRecord
from .utils import validate_and_change_password, check_old_password
from .verification.email_send import send_email
from .verification.sms_send import *


@api_view(['GET'])
@permission_classes([AllowAny])
def check_user(request):
    data = {}

    id_user = request.GET.get('userID', None)
    if id_user is None:
        data['success'] = False
        data['err'] = "Wrong User ID"
        return JsonResponse(json.dumps(data), safe=False)

    try:
        steam_id = CustomUser.objects.get(id=id_user).steam_id
    except Exception:
        data['success'] = False
        data['err'] = "Wrong User ID"
        return JsonResponse(json.dumps(data), safe=False)

    if steam_id is None or steam_id == "":
        data['success'] = False
    else:
        data['success'] = True

    return JsonResponse(json.dumps(data), safe=False)


@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
def sms_send(request):
    try:
        data = request.data
        phone_number = get_phone_number(data.get('phone_number'))

        user_id = int(data.get('user_id'))
        user = get_user_model().objects.get(pk=user_id)
        user.phone_number = phone_number
        sms_code = sms_code_gen(5)
        user.verfication_code = sms_code
        user.save()

        response = sms_sending(phone_number,
                               sms_code,
                               SMS_TEXT,
                               SMS_TRAFFIC_LOGIN,
                               SMS_TRAFFIC_PASS)
        status_code = response.status_code
        if status_code != 200:
            return Response('send_sms() problem', status=status.HTTP_400_BAD_REQUEST)

        return Response('good', status=status.HTTP_200_OK)
    except Exception as e:
        print(e.args[0] + ' sms_send() problem   Line-> ' + str(sys.exc_info()[2].tb_lineno))
        return Response(e.args[0] + ' sms_send() problem   Line-> ' + str(sys.exc_info()[2].tb_lineno))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_sms_code(request):
    user = None
    try:
        data = request.data
        sms_code = data.get('sms_code', None)
        user_id = int(data.get('user_id', None))
        if user_id is not None:
            user = get_user_model().objects.get(pk=user_id)
        if str(user.verfication_code) == sms_code and \
                user.verfication_code is not None:
            user.verified_phone = True
            user.save()
            return Response('good', status=status.HTTP_200_OK)
        else:
            return Response('incorrect sms code', status=status.HTTP_200_OK)
    except Exception as e:
        print(e.args[0] + ' verify_sms_code() problem   Line-> ' + str(sys.exc_info()[2].tb_lineno))
        return Response(e.args[0] + ' verify_sms_code() problem   Line-> ' + str(sys.exc_info()[2].tb_lineno))


@api_view(['POST'])
@permission_classes([AllowAny])
def restore_password(request):
    request_email = request.data.get('email', '')
    try:
        user = CustomUser.objects.get(email=request_email)
    except:
        return Response(data={"error": "User not found!"}, status=status.HTTP_400_BAD_REQUEST)

    restore_record = RestorePasswordRecord.objects.create(user=user)
    restore_link = f'{settings.FRONTEND_HOST}/recovery?token={restore_record.token}'
    email_message = f'Для восстановления пароля перейдите  {restore_link}'
    send_email(email=user.email, message=email_message, tittle='Восстановление пароля')
    return Response(status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def restore_password_submit(request):
    token = request.GET.get('token')

    try:
        restore_record = RestorePasswordRecord.objects.get(token=token, used=False)
    except:
        return Response(data={"error": "smth about token"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(status=status.HTTP_200_OK)
    elif request.method == 'POST':
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
    old_password = request.data.get('old_password', '')
    new_password = request.data.get('new_password', '')
    new_password_copy = request.data.get('new_password_copy', '')
    user = request.user

    check_old_password(user, password=old_password)
    validate_and_change_password(new_password,
                                 new_password_copy,
                                 user=user)
    login(request, user)
    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_id(request):
    return Response(data={'user_id': f"{request.user.username}@{request.user.id}"})
