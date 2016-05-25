"""
WSGI config for delft3dgtmain project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os

# Import settings before importing db, auth, or it will fail
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "delft3dgtmain.settings")

from django import db
from django.contrib import auth
from django.core.wsgi import get_wsgi_application
# from django.contrib.auth.handlers.modwsgi import check_password  # copied below


def check_password(environ, username, password):
    """
    Authenticates against Django's auth database
    mod_wsgi docs specify None, True, False as return value depending
    on whether the user exists and authenticates.

    Manually control this function instead of django
    in order to parse environ for correct path
    """

    UserModel = auth.get_user_model()
    # db connection state is managed similarly to the wsgi handler
    # as mod_wsgi may call these functions outside of a request/response cycle
    db.reset_queries()

    try:
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            return None
        if not user.is_active:
            return None

        # Method to deny access to specific directories
        #if "/tag0.1/scripts/visualisation" in environ['REQUEST_URI']:
        #    return None

        return user.check_password(password)
    finally:
        db.close_old_connections()

application = get_wsgi_application()
