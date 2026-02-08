#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Only apply gevent monkey patching for production (not for runserver)
# Gevent is used with gunicorn in production, not Django's dev server
if 'runserver' not in sys.argv:
    import gevent.monkey
    gevent.monkey.patch_socket()
    gevent.monkey.patch_ssl()


def main():
    """Run administrative tasks."""
    import logging

    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        level=logging.DEBUG
    )
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
