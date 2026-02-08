from rest_framework.serializers import ModelSerializer

from authentication.models import CustomUser
from .models import *

ALL_FIELDS = '__all__'


class UserVerificationSerializer(ModelSerializer):
    class Meta:
        model = UserVerification
        fields = ('id', 'is_verified', 'first_name', 'last_name', 'country_code', 'date_of_birth', 'gender',
                  'document_number', 'individual_identification_number', 'face_match_confidence')


class UserVerificationSerializerOnlyIsVerified(ModelSerializer):
    class Meta:
        model = UserVerification
        fields = ('id', 'is_verified')


class VerificationHistorySerializer(ModelSerializer):
    user_verification = UserVerificationSerializer()

    class Meta:
        model = CustomUser
        fields = ('id', 'verification_time', 'status', 'verification_id')
