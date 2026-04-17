import logging
import re
import secrets
import urllib.parse
from datetime import timedelta

import requests
from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import CustomUser, SteamPendingAuth

logger = logging.getLogger(__name__)

STEAM_OPENID_URL = 'https://steamcommunity.com/openid/login'
STEAM_ID_RE = re.compile(r'https://steamcommunity\.com/openid/id/(\d+)$')
STATE_TTL_MINUTES = 10


@api_view(['GET'])
@permission_classes([AllowAny])
def steam_connect(request):
    """
    Initiate Steam OpenID connection for an already-authenticated user.

    The frontend must pass the auth token as a query parameter:
      GET /auth/steam/?token=<auth_token>

    The view stores a random state in the DB, then redirects the browser
    to Steam so the user can authorise the connection.
    """
    token_key = request.GET.get('token')
    if not token_key:
        # Accept Authorization header too (for API clients / testing)
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            token_key = auth_header.split(' ', 1)[1]

    if not token_key:
        return Response({'error': 'Token required. Pass ?token=<auth_token>.'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        token = Token.objects.select_related('user').get(key=token_key)
    except Token.DoesNotExist:
        return Response({'error': 'Invalid token.'}, status=status.HTTP_401_UNAUTHORIZED)

    user = token.user
    if not user.is_active:
        return Response({'error': 'User is inactive.'}, status=status.HTTP_403_FORBIDDEN)

    # Clean up stale pending records for this user
    SteamPendingAuth.objects.filter(
        user=user,
        created_at__lt=timezone.now() - timedelta(minutes=STATE_TTL_MINUTES),
    ).delete()

    state = secrets.token_urlsafe(32)
    SteamPendingAuth.objects.create(user=user, state=state)

    callback_url = f"{settings.BACKEND_HOST}/auth/steam/callback/?state={state}"

    params = {
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'checkid_setup',
        'openid.return_to': callback_url,
        'openid.realm': settings.BACKEND_HOST + '/',
        'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
        'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
    }

    steam_url = STEAM_OPENID_URL + '?' + urllib.parse.urlencode(params)
    logger.info('steam_connect: redirecting user %s to Steam', user.id)
    return redirect(steam_url)


@api_view(['GET'])
@permission_classes([AllowAny])
def steam_callback(request):
    """
    Handle the Steam OpenID callback.

    Steam redirects here after the user authorises. We:
      1. Verify the OpenID response with Steam
      2. Extract the Steam64 ID
      3. Save it to the user record
      4. Redirect the browser back to the frontend profile page
    """
    state = request.GET.get('state')
    if not state:
        logger.warning('steam_callback: missing state param')
        return redirect(f"{settings.FRONTEND_HOST}/cabinet/profile?steam=error")

    # Look up and immediately delete the pending record (one-time use)
    try:
        pending = SteamPendingAuth.objects.select_related('user').get(state=state)
    except SteamPendingAuth.DoesNotExist:
        logger.warning('steam_callback: unknown or expired state %s', state)
        return redirect(f"{settings.FRONTEND_HOST}/cabinet/profile?steam=expired")

    # Check it hasn't expired (belt-and-suspenders; cleanup runs in steam_connect too)
    if pending.created_at < timezone.now() - timedelta(minutes=STATE_TTL_MINUTES):
        pending.delete()
        logger.warning('steam_callback: expired state %s', state)
        return redirect(f"{settings.FRONTEND_HOST}/cabinet/profile?steam=expired")

    user = pending.user
    pending.delete()

    # Verify the OpenID assertion with Steam
    verify_params = {k: v for k, v in request.GET.items()}
    verify_params['openid.mode'] = 'check_authentication'

    try:
        verify_response = requests.post(STEAM_OPENID_URL, data=verify_params, timeout=10)
    except requests.RequestException:
        logger.exception('steam_callback: Steam verification request failed')
        return redirect(f"{settings.FRONTEND_HOST}/cabinet/profile?steam=error")

    if 'is_valid:true' not in verify_response.text:
        logger.warning('steam_callback: Steam returned invalid for state %s', state)
        return redirect(f"{settings.FRONTEND_HOST}/cabinet/profile?steam=invalid")

    # Extract Steam64 ID from the claimed_id URL
    claimed_id = request.GET.get('openid.claimed_id', '')
    match = STEAM_ID_RE.match(claimed_id)
    if not match:
        logger.error('steam_callback: could not parse steam_id from claimed_id=%s', claimed_id)
        return redirect(f"{settings.FRONTEND_HOST}/cabinet/profile?steam=error")

    steam64_id = match.group(1)

    user.steam_id = steam64_id
    user.save(update_fields=['steam_id'])
    logger.info('steam_callback: linked steam_id=%s to user %s', steam64_id, user.id)

    return redirect(f"{settings.FRONTEND_HOST}/cabinet/profile?steam=connected")
