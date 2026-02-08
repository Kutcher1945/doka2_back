import os

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

client = Client(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_AUTH_TOKEN'])
verify = client.verify.services(os.environ['TWILIO_VERIFY_SERVICE_SID'])


def send_verification_sms(phone):
    verify.verifications.create(to=phone, channel='sms')


def check_verification_code(phone, code):
    try:
        result = verify.verification_checks.create(to=phone, code=code)
    except TwilioRestException:
        print('no')
        return False
    return result.status == 'approved'
