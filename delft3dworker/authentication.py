from rest_framework.authentication import SessionAuthentication
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
import logging


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening


class MyDeltaresOnlyOIDC(OIDCAuthenticationBackend):
    def create_user(self, claims):
        """Create read-only user."""
        email = claims.get("email")
        if not email.endswith("@deltares.nl"):
            logging.warning("Only Deltares users can create users")
            return None

        user = super(MyDeltaresOnlyOIDC, self).create_user(claims)
        user.save()

        return user
