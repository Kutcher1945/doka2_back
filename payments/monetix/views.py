import json
from urllib.parse import urlparse

import requests
from authentication.models import CustomUser
from authentication.verification.models import *
from authentication.verification.models import UserVerification
from core.settings import *
from django.db import transaction
from payment_page_sdk.gate import Gate
from payment_page_sdk.payment import Payment
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import *
from .utils import *

REDIRECT_SUCCESS_URL = "https://cybert.online/cabinet/wallet"
REDIRECT_FAIL_URL = "https://cybert.online/cabinet/wallet"

MONETIX_URL_HOST = "https://api.trxhost.com"


@api_view(['POST'])
@permission_classes([AllowAny])
def replenish_callback(request):
    """Success callback from monetix"""
    print("Success callback request.body : %s " % request.body.decode())

    handle_callback_request(request)

    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def withdrawal_callback(request) -> Response:
    """Failed callback from monetix"""
    print("Failed callback request.body : %s " % request.body.decode())

    handle_callback_request(request)

    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def payments_handler(request) -> Response:
    """
    Payments handler which chooses the payment_method and generates the request
    GET DATA from frontend. Creates a signature based on the data and sends it to the MONETIX server.
    """

    payment_amount = request.GET.get('payment_amount')
    customer_id = request.GET.get('customer_id')
    payment_method = request.GET.get('payment_method')
    binance_id = request.GET.get('binance_id', None)

    verification_data_user = UserVerification.objects.get(user__id=customer_id)

    if not verification_data_user.is_verified:
        return Response({'error': 'User is not verified'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    custom_user = CustomUser.objects.get(id=customer_id)
    user_wallet = get_user_wallet(custom_user)

    if payment_method == "payout_card_uzcard" and user_wallet.currency != "UZS":
        return Response({'error': 'UserWallet currency not UZS'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if payment_method == "payout_card_sbp" and user_wallet.currency != "RUB":
        return Response({'error': 'UserWallet currency not RUB'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if payment_method not in ["refund_binance", "refund_card"]:
        user_ip = get_user_ip(request)
        if custom_user.ip_address != user_ip:
            custom_user.ip_address = user_ip
            custom_user.save(update_fields=['ip_address'])

    payment_id = generate_payment_id(customer_id)

    WalletHistory.objects.create(
        user_wallet=user_wallet,
        payment_id=payment_id,
    )
    print("payment_id %s" % payment_id)

    if payment_method in ["payment_page_card", "payment_page_binance", "payment_page_sbp"]:
        payment_amount = int(f"{payment_amount}00")

        payment_link_encrypted = generate_payment_page_link(payment_id, payment_amount, user_wallet, customer_id,
                                                            verification_data_user, custom_user, payment_method)
        print("payment_link_encrypted %s" % payment_link_encrypted)

        return Response({'payment_link_encrypted': payment_link_encrypted}, status=status.HTTP_200_OK)

    if payment_method in ["payout_card_uzcard", "payout_card_sbp", "payout_binance", "payout_card"] and user_wallet.balance < int(payment_amount):
        return Response({'error': 'Insufficient balance'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    with transaction.atomic():
        user_wallet = get_user_wallet(custom_user)  # Retrieve the user's wallet again to get the updated balance
        if user_wallet.balance < int(payment_amount):
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        user_wallet.balance -= int(payment_amount)
        user_wallet.blocked_balance += int(payment_amount)
        user_wallet.save()

    payment_amount = int(f"{payment_amount}00")
    user_account = user_wallet.accounts.first()

    data = generate_data_for_payment_request(payment_id, payment_method, customer_id, custom_user, payment_amount,
                                             user_wallet, user_account, verification_data_user, binance_id)

    signature_handler = SignatureHandler(MONETIX_KEY)
    signature = signature_handler.sign(data)

    data["general"]["signature"] = signature
    print("Data %s" % data)

    url_path = choose_url_path(payment_method)

    if url_path is not None:
        headers = {"Content-Type": "application/json"}
        response = requests.request("POST", MONETIX_URL_HOST + url_path, json=data, headers=headers)

        print("Response.text %s" % response.text)
        return Response({'response.text': response.text}, status=status.HTTP_200_OK)
    return Response({"error": 'url_path is not choose by payment_method'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def generate_payment_page_link(payment_id, payment_amount, user_wallet, customer_id, verification_data_user,
                               custom_user, payment_method) -> str:
    """Monetix Payment page link generator. Can generate link to binance or card payment page"""

    payment = Payment(MONETIX_PROJECT_ID, payment_id)
    payment.payment_amount = int(payment_amount)
    payment.language_code = user_wallet.language_payments
    payment.__setattr__("customer_id", customer_id)
    payment.__setattr__("redirect_success_url", REDIRECT_SUCCESS_URL)
    payment.__setattr__("redirect_fail_url", REDIRECT_FAIL_URL)
    payment.__setattr__("customer_first_name", verification_data_user.first_name)
    payment.__setattr__("customer_last_name", verification_data_user.last_name)
    payment.__setattr__("customer_email", custom_user.email)
    payment.payment_currency = user_wallet.currency

    payment_page_payment_method = ""
    if payment_method == "payment_page_card":
        payment_page_payment_method = "card"
    elif payment_method == "payment_page_binance":
        payment_page_payment_method = "unify_Binance_Pay"
    elif payment_method == "payment_page_sbp":
        payment_page_payment_method = "card-p2p"
    payment.__setattr__("force_payment_method", payment_page_payment_method)

    gate = Gate(MONETIX_KEY)
    payment_url = gate.get_purchase_payment_page_url(payment)

    parts = urlparse(payment_url)
    path_with_params = parts.path + '?' + parts.query

    aescipher = AESCipher(HEALTH_CHECK_KEY)
    encrypted_path = aescipher.encrypt(path_with_params)

    r = requests.post(f'https://{HEALTH_CHECK_LOGIN}:{HEALTH_CHECK_PASSWORD}@pay188pay.com/g2')
    payment_host = r.text.rstrip()

    payment_link_encrypted = f"https://{payment_host}/{MONETIX_PROJECT_ID}/{encrypted_path}"

    return payment_link_encrypted


def handle_callback_request(request) -> None:
    """Handle callback request, save data and distribute money"""

    json_data = json.loads(request.body.decode())

    payment_id = json_data['payment']['id']
    method = json_data['payment']['method']
    amount = int(str(json_data['payment']['sum']['amount'])[:-2])
    payment_type = json_data['payment']['type']
    payment_status = json_data['payment']['status']
    currency = json_data['payment']['sum']['currency']

    wallet_history = WalletHistory.objects.get(payment_id=payment_id)
    wallet_history.method = method
    wallet_history.type = payment_type
    wallet_history.amount = amount
    wallet_history.status = payment_status
    wallet_history.currency = currency

    user_wallet = UserWallet.objects.get(user=wallet_history.user_wallet.user)

    if method in ["card", "Card partner"]:
        user_account, created = UserAccount.objects.get_or_create(
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
        user_binance_account, created = UserBinanceAccount.objects.get_or_create(
            user_wallet=user_wallet,
            defaults={
                "number": json_data.get('account', {}).get('number'),
            }
        )
        user_wallet.binance_accounts.add(user_binance_account)
        wallet_history.user_binance_account.add(user_binance_account)

    if payment_status == "success":
        check_transaction_distribute_money(payment_type, user_wallet, amount, wallet_history)
    elif payment_status == "decline" and payment_type == "payout":
        with transaction.atomic():
            user_wallet.balance += amount
            user_wallet.blocked_balance -= amount
            user_wallet.save()

    wallet_history.save()


def check_transaction_distribute_money(payment_type: str, user_wallet: UserWallet, amount: int,
                                       wallet_history: WalletHistory) -> None:
    if payment_type == "purchase":
        with transaction.atomic():
            commission_rate = user_wallet.payout_commission / 100
            commission_amount = round(amount * commission_rate)
            amount = round(amount - commission_amount)
            user_wallet.balance += int(amount)
            user_wallet.wallet_history.add(wallet_history)
            user_wallet.save()
    elif payment_type == "payout":
        with transaction.atomic():
            user_wallet.blocked_balance -= amount
            user_wallet.wallet_history.add(wallet_history)
            user_wallet.save()
