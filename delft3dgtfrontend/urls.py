from django.conf import settings  # noqa
from django.conf.urls import url  # noqa
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.views.static import serve

from django.contrib.auth.views import login
from django.contrib.auth.views import logout

urlpatterns = (
    # Examples:

    url(r'^login/$', login),
    url(r'^logout/$', logout),

    url(r'^$', login_required(serve), {
        'document_root': settings.FRONTEND_STATIC_FILES,
        'path': 'index.html'
    }),

    url(r'^(?P<path>.*)$', login_required(serve), {
        'document_root': settings.FRONTEND_STATIC_FILES,
    }),

)
