"""
WSGI config for delft3dgtmain project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

from __future__ import absolute_import
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "delft3dgtmain.settings"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
