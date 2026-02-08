# command = '/venv/bin/gunicorn'
bind = '0.0.0.0:8000'
workers = 3
timeout = 120
user = 'root'
limit_request_fields = 32000
limit_request_field_size = 0
raw_env = 'DJANGO_SETTINGS_MODULE=core.settings'
