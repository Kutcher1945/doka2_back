from django.urls import path

from achievements.views import give_user_bonus_for_registration

urlpatterns = [
    path('give_user_bonus_for_registration/', give_user_bonus_for_registration),
]
