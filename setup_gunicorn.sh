#!/bin/sh
# python manage.py migrate --noinput
exec gunicorn -c "gunicorn_config.py" core.wsgi