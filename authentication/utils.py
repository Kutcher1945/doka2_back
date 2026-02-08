from rest_framework.exceptions import ParseError


def validate_and_change_password(password, password_copy, user):
    password_valid, reason = validate_password(password,
                                               password_copy)
    if not password_valid:
        raise ParseError(detail={"error": reason})
    print("user: %s" % user)
    user.set_password(password)
    user.save()


def check_old_password(user, password):
    valid = user.check_password(password)
    if not valid:
        raise ParseError(detail={"error": "Incorrect old password!"})


def validate_password(password, password_copy) -> tuple:
    if password != password_copy:
        return False, "Passwords do not match!"
    if len(password) < 8:
        return False, "Password less than 8 characters!"
    return True, ''
