from __future__ import absolute_import
from django.conf import settings  # noqa
from django.conf.urls import url  # noqa
from django.contrib.auth.decorators import login_required
from django.views.static import serve

from django.contrib.auth.views import login
from django.contrib.auth.views import logout
from django.contrib.auth.views import password_reset
from django.contrib.auth.views import password_reset_complete
from django.contrib.auth.views import password_reset_confirm
from django.contrib.auth.views import password_reset_done

urlpatterns = (

    # Login
    url(r'^login/$', login, {'template_name': 'login.html'},
        name="login"),

    # Logout
    url(r'^logout/$', logout, {'template_name': 'login.html'},
        name="logout"),

    # Password Reset
    url(r'^forgot/$', password_reset, {'template_name': 'forgot.html'},
        name="password_reset"),

    # Password Reset Done
    url(r'^done/$', password_reset_done, {'template_name': 'done.html'},
        name="password_reset_done"),

    # Password Reset Done
    url(r'^reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$', password_reset_confirm,
        {'template_name' : 'confirm.html'}, name="password_reset_confirm"),

    # Password Reset Complete
    url(r'^complete/$', password_reset_complete, {'template_name' : 'complete.html'},
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
