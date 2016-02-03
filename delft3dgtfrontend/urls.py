from django.conf.urls import url  # noqa
from django.views.generic import TemplateView

from delft3dgtfrontend.views import home

urlpatterns = (
    # Examples:

    url(r'^$', TemplateView.as_view(template_name="index.html"), name='home'),
)
