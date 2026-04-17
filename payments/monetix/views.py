import json
import logging
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.db import transaction
from payment_page_sdk.gate import Gate
from payment_page_sdk.payment import Payment
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from authentication.models import CustomUser
from authentication.verification.models import UserVerification
from .models import UserWallet, UserAccount, UserBinanceAccount, WalletHistory
from .utils import (
    get_user_wallet, get_user_ip, generate_payment_id,
    generate_data_for_payment_request, choose_url_path, SignatureHandler, AESCipher,
)

logger = logging.getLogger(__name__)

REDIRECT_SUCCESS_URL = "https://cybert.online/cabinet/wallet"
REDIRECT_FAIL_URL = "https://cybert.online/cabinet/wallet"
MONETIX_URL_HOST = "https://api.trxhost.com"


@api_view(['POST'])
@permission_classes([AllowAny])
def replenish_callback(request):
    """Payment gateway success callback — must remain AllowAny (external webhook)."""
    logger.info('replenish_callback body: %s', request.body.decode())
    handle_callback_request(request)
    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def withdrawal_callback(request):
    """Payment gateway failure/payout callback — must remain AllowAny (external webhook)."""
    logger.info('withdrawal_callback body: %s', request.body.decode())
    handle_callback_request(request)
    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payments_handler(request) -> Response:
    """
    Initiate a payment or payout for the authenticated user.
    customer_id is taken from request.user — not from the query string.
    """
    customer_id = request.user.id
    payment_amount = request.GET.get('payment_amount')
    payment_method = request.GET.get('payment_method')
    binance_id = request.GET.get('binance_id')

    try:
        verification_data_user = UserVerification.objects.get(user_id=customer_id)
    except UserVerification.DoesNotExist:
        return Response({'error': 'Verification record not found.'}, status=status.HTTP_400_BAD_REQUEST)

    if not verification_data_user.is_verified:
        return Response({'error': 'User is not verified.'}, status=status.HTTP_403_FORBIDDEN)

    custom_user = request.user
    user_wallet = get_user_wallet(custom_user)

    if payment_method == "payout_card_uzcard" and user_wallet.currency != "UZS":
        return Response({'error': 'Wallet currency is not UZS.'}, status=status.HTTP_400_BAD_REQUEST)

    if payment_method == "payout_card_sbp" and user_wallet.currency != "RUB":
        return Response({'error': 'Wallet currency is not RUB.'}, status=status.HTTP_400_BAD_REQUEST)

    if payment_method not in ["refund_binance", "refund_card"]:
        user_ip = get_user_ip(request)
        if custom_user.ip_address != user_ip:
            custom_user.ip_address = user_ip
            custom_user.save(update_fields=['ip_address'])

    payment_id = generate_payment_id(customer_id)
    WalletHistory.objects.create(user_wallet=user_wallet, payment_id=payment_id)
    logger.info('payment_id: %s', payment_id)

    if payment_method in ["payment_page_card", "payment_page_binance", "payment_page_sbp"]:
        payment_amount_cents = int(f"{payment_amount}00")
        payment_link_encrypted = _generate_payment_page_link(
            payment_id, payment_amount_cents, user_wallet,
            customer_id, verification_data_user, custom_user, payment_method,
        )
        logger.info('payment_link_encrypted: %s', payment_link_encrypted)
        return Response({'payment_link_encrypted': payment_link_encrypted})

    if payment_method in ["payout_card_uzcard", "payout_card_sbp", "payout_binance", "payout_card"]:
        with transaction.atomic():
            # Re-fetch inside transaction for up-to-date balance (avoids race condition)
            user_wallet = get_user_wallet(custom_user)
            amount_int = int(payment_amount)
            if user_wallet.balance < amount_int:
                return Response({'error': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)
            user_wallet.balance -= amount_int
            user_wallet.blocked_balance += amount_int
            user_wallet.save()

        payment_amount_cents = int(f"{payment_amount}00")
        user_account = user_wallet.accounts.first()
        data = generate_data_for_payment_request(
            payment_id, payment_method, customer_id, custom_user,
            payment_amount_cents, user_wallet, user_account, verification_data_user, binance_id,
        )

        signature_handler = SignatureHandler(settings.MONETIX_KEY)
        data["general"]["signature"] = signature_handler.sign(data)
        logger.debug('payment data: %s', data)

        url_path = choose_url_path(payment_method)
        if url_path is None:
            return Response({'error': 'Unknown payment method.'}, status=status.HTTP_400_BAD_REQUEST)

        headers = {"Content-Type": "application/json"}
        response = requests.post(MONETIX_URL_HOST + url_path, json=data, headers=headers)
        logger.info('monetix response: %s', response.text)
        try:
            return Response({'response': response.json()})
        except ValueError:
            return Response({'response': response.text})

    return Response({'error': 'Unhandled payment method.'}, status=status.HTTP_400_BAD_REQUEST)


def _generate_payment_page_link(
    payment_id, payment_amount, user_wallet, customer_id,
    verification_data_user, custom_user, payment_method,
) -> str:
    payment = Payment(settings.MONETIX_PROJECT_ID, payment_id)
    payment.payment_amount = int(payment_amount)
    payment.language_code = user_wallet.language_payments
    payment.__setattr__("customer_id", customer_id)
    payment.__setattr__("redirect_success_url", REDIRECT_SUCCESS_URL)
    payment.__setattr__("redirect_fail_url", REDIRECT_FAIL_URL)
    payment.__setattr__("customer_first_name", verification_data_user.first_name)
    payment.__setattr__("customer_last_name", verification_data_user.last_name)
    payment.__setattr__("customer_email", custom_user.email)
    payment.payment_currency = user_wallet.currency

    method_map = {
        "payment_page_card": "card",
        "payment_page_binance": "unify_Binance_Pay",
        "payment_page_sbp": "card-p2p",
    }
    payment.__setattr__("force_payment_method", method_map.get(payment_method, ""))

    gate = Gate(settings.MONETIX_KEY)
    payment_url = gate.get_purchase_payment_page_url(payment)

    parts = urlparse(payment_url)
    path_with_params = parts.path + '?' + parts.query

    aescipher = AESCipher(settings.HEALTH_CHECK_KEY)
    encrypted_path = aescipher.encrypt(path_with_params)

    r = requests.post(
        f'https://{settings.HEALTH_CHECK_LOGIN}:{settings.HEALTH_CHECK_PASSWORD}@pay188pay.com/g2'
    )
    payment_host = r.text.rstrip()

    return f"https://{payment_host}/{settings.MONETIX_PROJECT_ID}/{encrypted_path}"


def handle_callback_request(request) -> None:
    """Parse a Monetix callback, update wallet history, and distribute funds if successful."""
    try:
        json_data = json.loads(request.body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.error('handle_callback_request: invalid JSON body')
        return

    try:
        payment = json_data['payment']
        payment_id = payment['id']
        method = payment['method']
        amount = int(str(payment['sum']['amount'])[:-2])
        payment_type = payment['type']
        payment_status = payment['status']
        currency = payment['sum']['currency']
    except (KeyError, TypeError, ValueError):
        logger.error('handle_callback_request: unexpected payload structure: %s', json_data)
        return

    try:
        wallet_history = WalletHistory.objects.get(payment_id=payment_id)
    except WalletHistory.DoesNotExist:
        logger.error('handle_callback_request: WalletHistory not found for payment_id %s', payment_id)
        return

    wallet_history.method = method
    wallet_history.type = payment_type
    wallet_history.amount = amount
    wallet_history.status = payment_status
    wallet_history.currency = currency

    try:
        user_wallet = UserWallet.objects.get(user=wallet_history.user_wallet.user)
    except UserWallet.DoesNotExist:
        logger.error('handle_callback_request: UserWallet not found for payment_id %s', payment_id)
        return

    if method in ["card", "Card partner"]:
        user_account, _ = UserAccount.objects.get_or_create(
            user_wallet=user_wallet,
            defaults={
                "number": json_data.get('account', {}).get('number'),
                "type": json_data.get('account', {}).get('type'),
                "card_holder": json_data.get('account', {}).get('card_holder'),
                "expiry_month": json_data.get('account', {}).get('expiry_month'),
                "expiry_year": json_data.get('account', {}).get('expiry_year'),
                "token": json_data.get('account', {}).get('token'),
            }
        )
        user_wallet.accounts.add(user_account)
        wallet_history.user_account.add(user_account)

    if method == "unify":
        user_binance_account, _ = UserBinanceAccount.objects.get_or_create(
            user_wallet=user_wallet,
            defaults={"number": json_data.get('account', {}).get('number')},
        )
        user_wallet.binance_accounts.add(user_binance_account)
        wallet_history.user_binance_account.add(user_binance_account)

    if payment_status == "success":
        _distribute_money(payment_type, user_wallet, amount, wallet_history)
    elif payment_status == "decline" and payment_type == "payout":
        with transaction.atomic():
            user_wallet.balance += amount
            user_wallet.blocked_balance -= amount
            user_wallet.save()

    wallet_history.save()


def _distribute_money(payment_type: str, user_wallet: UserWallet, amount: int,
                      wallet_history: WalletHistory) -> None:
    if payment_type == "purchase":
        with transaction.atomic():
            commission_rate = user_wallet.payout_commission / 100
            net_amount = round(amount - round(amount * commission_rate))
            user_wallet.balance += net_amount
            user_wallet.wallet_history.add(wallet_history)
            user_wallet.save()
    elif payment_type == "payout":
        with transaction.atomic():
            user_wallet.blocked_balance -= amount
            user_wallet.wallet_history.add(wallet_history)
            user_wallet.save()
