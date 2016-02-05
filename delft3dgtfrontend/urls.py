from django.conf.urls import url  # noqa
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from django.contrib.auth.views import login
from django.contrib.auth.views import logout

urlpatterns = (
    # Examples:

    url(r'^$', login_required(TemplateView.as_view(template_name="index.html")), name='home'),

    url(r'^login/$', login),
    url(r'^logout/$', logout),

)
