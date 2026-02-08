import base64
import hashlib
import hmac
import random
from collections import OrderedDict

from Crypto import Random
from Crypto.Cipher import AES
from authentication.models import CustomUser
from core.settings import *
from django.http import HttpRequest

from .models import UserWallet

MONETIX_URLS = {
    "payout_card": "/v2/payment/card/payout/token",
    "refund_card": "/v2/payment/card/refund",
    "tokenize": "/v2/customer/card/tokenize",
    "payout_binance": "/v2/payment/unify/payout",
    "refund_binance": "/v2/payment/unify/refund",
    "payout_card_uzcard": "/v2/payment/card-partner/payout",
    "payout_card_sbp": "/v2/payment/card-p2p/payout",
}


def choose_url_path(payment_method: str) -> str:
    return MONETIX_URLS.get(payment_method, "")


def generate_data_for_payment_request(payment_id, payment_method, customer_id, custom_user, payment_amount, user_wallet,
                                      user_account, verification_data_user, binance_id):
    """
    Generate data for request to MONETIX.
    Params taken from: https://developers.trxhost.com/
    """

    data = {
        "general": {
            "project_id": int(MONETIX_PROJECT_ID),
            "payment_id": payment_id
        },
        "payment": {
            "amount": payment_amount,
            "currency": user_wallet.currency
        }
    }

    if payment_method not in ["refund_card", "refund_binance"]:
        data["customer"] = {
            "id": str(customer_id),
            "ip_address": custom_user.ip_address,
            "first_name": verification_data_user.first_name,
            "last_name": verification_data_user.last_name,
            "email": custom_user.email
        }

    if payment_method == "refund_binance" or payment_method == "payout_binance":
        data["payment"]["by_method"] = "BinancePay"

    if payment_method == "payout_card":
        data["account"] = {
            "card_holder": user_account.card_holder
        }
        data["interface_type"] = {
            "id": 7
        }
        data["token"] = user_account.token
    elif payment_method == "payout_binance":
        data["account"] = {
            "number": str(binance_id)
        }
        data["payment_data"] = {
            "receive_type": "Pay_ID"
        }
    elif payment_method == "payout_card_uzcard":
        data["account"] = {
            "number": user_account.token
        }
    elif payment_method == "refund_card":
        data["payment"]["description"] = "refund"

    print("data %s " % data)

    return data


def get_user_ip(request: HttpRequest) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_wallet(custom_user: CustomUser) -> UserWallet:
    """Get user wallet and if not exist create it"""
    user_wallet, created = UserWallet.objects.get_or_create(user=custom_user)

    if created:
        custom_user.user_wallet = user_wallet
        custom_user.save()

    return user_wallet


def generate_payment_id(customer_id: int) -> str:
    return MONETIX_TRANSACTION_TYPE + "_" + str(customer_id) + "_" + str(random.randint(0, 9999999))


class AESCipher(object):

    def __init__(self, key):
        self.bs = AES.block_size
        self.key = key.encode()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        encoded = base64.b64encode(cipher.encrypt(raw.encode()))
        return base64.b64encode((encoded.decode() + "::" + base64.b64encode(iv).decode()).encode()).decode()

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]


class SignatureHandler(object):
    """Class SignatureHandler

    Attributes:
        ITEMS_DELIMITER - signature concatenation delimiter
        IGNORE_KEYS - ignore keys in signature

        __secretKey - Secret key
    """
    ITEMS_DELIMITER = ';'
    IGNORE_KEYS = ['frame_mode']

    __secretKey = None

    def __init__(self, secret_key: str):
        """
        SignatureHandler constructor

        :param str secret_key:
        """
        self.__secretKey = secret_key

    def sign(self, params: dict) -> str:
        """
        Return signature

        :param params:
        :return:
        """
        secret_key = self.__secretKey.encode('utf-8')

        params_to_sign = self.__get_params_to_sign(params, self.IGNORE_KEYS)

        params_to_sign_list = list(OrderedDict(sorted(params_to_sign.items(), key=lambda t: t[0])).values())

        string_to_sign = self.ITEMS_DELIMITER.join(params_to_sign_list).encode('utf-8')

        return base64.b64encode(hmac.new(secret_key, string_to_sign, hashlib.sha512).digest()).decode()

    def __get_params_to_sign(self, params: dict, ignore=None, prefix='', sort=True) -> dict:
        """
        Get parameters to sign

        :param params:
        :param ignore:
        :param prefix:
        :param sort:
        :return:
        """
        if ignore is None:
            ignore = []

        params_to_sign = {}

        for key in params:
            if key in ignore:
                continue

            param_key = prefix + (':' if prefix else '') + key
            value = params[key]

            if isinstance(value, list):
                value = {str(key): value for key, value in enumerate(value)}

            if isinstance(value, dict):
                sub_array = self.__get_params_to_sign(value, ignore, param_key, False)
                params_to_sign.update(sub_array)
            else:
                if isinstance(value, bool):
                    value = '1' if value else '0'
                elif value is None:
                    value = ''
                else:
                    value = str(value)
                params_to_sign[param_key] = param_key + ':' + value

        if sort:
            sorted(params_to_sign.items(), key=lambda item: item[0])

        return params_to_sign
