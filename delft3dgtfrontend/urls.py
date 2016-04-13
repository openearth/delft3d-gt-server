from django.conf import settings  # noqa
from django.conf.urls import url  # noqa
from django.contrib.auth.decorators import login_required
from django.views.static import serve

from django.contrib.auth.views import login
from django.contrib.auth.views import logout

from .views import export

urlpatterns = (

    # Login
    url(r'^login/$', login, {'template_name': 'login.html'}),
    url(r'^login/(?P<path>.*)$', serve, {
        'document_root': settings.LOGIN_STATIC_FILES,
    }),

    # Logout
    url(r'^logout/$', logout),
    url(r'^export/(?P<scene>.*)/(?P<selection>.*)', export),

    # Index
    url(r'^$', login_required(serve), {
        'document_root': settings.FRONTEND_STATIC_FILES,
        'path': 'index.html'
    }),
    url(r'^(?P<path>.*)$', login_required(serve), {
        'document_root': settings.FRONTEND_STATIC_FILES,
    }),

)
