from django.core.mail import send_mail


def send_email(email, message, tittle):
    send_mail(
        tittle,
        message,
        'cybert.helper@gmail.com',
        [email],
        fail_silently=False,
    )
