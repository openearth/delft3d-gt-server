from django.conf import settings  # noqa
from django.conf.urls import url  # noqa
from django.contrib.auth.decorators import login_required
from django.views.static import serve

from django.contrib.auth.views import login
from django.contrib.auth.views import logout
from django.contrib.auth.views import password_reset
from django.contrib.auth.views import password_reset_done

urlpatterns = (

    # Login
    url(r'^login/$', login, {'template_name': 'login.html'},
        name="login"),
    url(r'^login/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT
    }),

    # Logout
    url(r'^logout/$', logout, {'template_name': 'login.html'},
        name="logout"),
    url(r'^logout/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT
    }),

    # Password Reset
    url(r'^forgot/$', password_reset, {'template_name': 'forgot.html'},
        name="password_reset"),
    url(r'^forgot/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT
    }),

    # Password Reset Done
    url(r'^done/$', password_reset_done, {'template_name': 'done.html'},
        name="password_reset_done"),
    url(r'^done/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT
    }),

    # Index
    url(r'^$', login_required(serve), {
        'document_root': settings.STATIC_ROOT,
        'path': 'index.html'
    }),
    url(r'^(?P<path>.*)$', login_required(serve), {
        'document_root': settings.STATIC_ROOT
    }),

)
