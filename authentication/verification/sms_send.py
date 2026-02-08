import random
import sys

import requests
from lxml import objectify as xml_objectify

SMS_TEXT = 'Номер подтверждения: '
SMS_TRAFFIC_LOGIN = 'rid_kz'
SMS_TRAFFIC_PASS = 'u86w24Wk'
SMS_TRAFFIC_URL = 'http://api.smstraffic.ru/multi.php'


def xml_to_dict(xml_str):
    """ Convert xml to dict, using lxml v3.4.2 xml processing library """

    def xml_to_dict_recursion(xml_object):
        dict_object = xml_object.__dict__
        if not dict_object:
            return xml_object
        for key, value in dict_object.items():
            dict_object[key] = xml_to_dict_recursion(value)
        return dict_object

    return xml_to_dict_recursion(xml_objectify.fromstring(xml_str))


def sms_code_gen(max_number_digits):
    l_num = [x for x in range(10)]
    sms_code = []
    for i in range(max_number_digits):
        number = random.choice(l_num)
        sms_code.append(number)
        strings = [str(integer) for integer in sms_code]
        fin_sms_code = "".join(strings)
    return fin_sms_code


def get_phone_number(number):
    """from str phone number to integer format. Clean from symbols"""
    normal_number = ''
    if isinstance(number, str):
        final_number = ''
        normal_number = [int(s) for s in number if s.isdigit()]
        strings = [str(integer) for integer in normal_number]
        final_number = "".join(strings)
        # final_number = int(a_string)
    if isinstance(number, int):
        final_number = number
    return final_number


def sms_sending(phone, sms_code, sms_text, sms_login, sms_password, ignore_phone_format=0):
    """
    concerning parameters: rus  => checkout API manual of smstraffic.ru

    ignore_phone_format => if 0 = wrong format of the phone returns error and stop send  sms process,
     if 1 = send sms anyway to the wrong format of the phone
    """
    message = sms_text + sms_code
    try:
        response = requests.post(SMS_TRAFFIC_URL, data={'login': sms_login,
                                                        'password': sms_password,
                                                        'phones': phone,
                                                        'message': message,
                                                        'ignore_phone_format': ignore_phone_format,
                                                        'rus': 5
                                                        },
                                 headers={'Connection': 'close'})

    except Exception as e:
        print(e.args[0] + ' sms_sending   Line-> ' + str(sys.exc_info()[2].tb_lineno))
        response = 'No connection with sms center'

    return response
