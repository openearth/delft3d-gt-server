from django.conf.urls import url  # noqa
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

urlpatterns = (
    # Examples:

    url(r'^$', login_required(TemplateView.as_view(template_name="index.html")), name='home'),

    url(r'^login/$', 'django.contrib.auth.views.login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout'),

)
