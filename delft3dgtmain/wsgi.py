"""
WSGI config for delft3dgtmain project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os

# Import settings before importing db, auth, or it will fail
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "delft3dgtmain.settings")

from django.contrib.auth.handlers.modwsgi import check_password

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()
