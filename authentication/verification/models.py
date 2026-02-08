import uuid

from django.db import models


class UserVerification(models.Model):
    user = models.ForeignKey("authentication.CustomUser", on_delete=models.CASCADE, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    date_of_birth = models.CharField(max_length=10, null=True, blank=True)
    gender = models.CharField(max_length=5, null=True, blank=True)
    document_number = models.CharField(max_length=15, null=True, blank=True)
    individual_identification_number = models.CharField(max_length=12, null=True, blank=True)
    face_match_confidence = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} "

    @property
    def check_is_verified(self):
        return self.is_verified


class VerificationHistory(models.Model):
    user_verification = models.ForeignKey(UserVerification, on_delete=models.SET_NULL, null=True, blank=True)
    verification_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    verification_id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=255)

    def __str__(self):
        return f"{self.user_verification} : {self.verification_id}"
