import logging

from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening


class MyDeltaresOnlyOIDC(OIDCAuthenticationBackend):
    def create_user(self, claims):
        """Create read-only user."""
        user = super(MyDeltaresOnlyOIDC, self).create_user(claims)
        user.save()

        # Give user restricted view rights by default
        world_restricted = Group.objects.filter(name="access:world_restricted").first()
        if world_restricted is not None:
            world_restricted.user_set.add(user)
        else:
            logging.warning("No restricted world group available!")

        return user
