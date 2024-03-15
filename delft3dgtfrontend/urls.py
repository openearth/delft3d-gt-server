from __future__ import absolute_import

from django.conf import settings  # noqa
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import re_path  # noqa
from django.urls import path
from django.views.static import serve

urlpatterns = (
    # Login
    path("login/", LoginView.as_view(template_name="login.html"), name="login"),
    # Logout
    path("logout/", LogoutView.as_view(template_name="login.html"), name="logout"),
    # Password Reset
    path(
        "forgot/",
        PasswordResetView.as_view(template_name="forgot.html"),
        name="password_reset",
    ),
    # Password Reset Done
    path(
        "done/",
        PasswordResetDoneView.as_view(template_name="done.html"),
        name="password_reset_done",
    ),
    # Password Reset Done
    re_path(
        r"^reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
        PasswordResetConfirmView.as_view(template_name="confirm.html"),
        name="password_reset_confirm",
    ),
    # Password Reset Complete
    path(
        "complete/",
        PasswordResetCompleteView.as_view(template_name="complete.html"),
        name="password_reset_complete",
    ),
    # Index
    path(
        "",
        login_required(serve),
        {"document_root": settings.STATIC_ROOT, "path": "index.html"},
    ),
    # static files/
    re_path(r"^(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
)
