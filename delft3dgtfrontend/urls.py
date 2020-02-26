from __future__ import absolute_import
from django.conf import settings  # noqa
from django.conf.urls import url  # noqa
from django.contrib.auth.decorators import login_required
from django.views.static import serve

from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.views import PasswordResetCompleteView
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.views import PasswordResetDoneView

urlpatterns = (

    # Login
    url(r'^login/$', LoginView.as_view(template_name='login.html'),
        name="login"),

    # Logout
    url(r'^logout/$', LogoutView.as_view(template_name='login.html'),
        name="logout"),

    # Password Reset
    url(r'^forgot/$', PasswordResetView.as_view(template_name='forgot.html'),
        name="password_reset"),

    # Password Reset Done
    url(r'^done/$', PasswordResetDoneView.as_view(template_name='done.html'),
        name="password_reset_done"),

    # Password Reset Done
    url(r'^reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$', PasswordResetConfirmView.as_view(template_name=
        'confirm.html'), name="password_reset_confirm"),

    # Password Reset Complete
    url(r'^complete/$', PasswordResetCompleteView.as_view(template_name='complete.html'),
        name="password_reset_complete"),

    # Index
    url(r'^$', login_required(serve), {
        'document_root': settings.STATIC_ROOT,
        'path': 'index.html'
    }),

    # static files/
    url(r'^(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT
    }),
)
