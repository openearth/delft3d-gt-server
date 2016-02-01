from django.conf.urls import include, url, handler404, handler500  # noqa
from taskmanager.views import runs
from taskmanager.views import createrun
from taskmanager.views import deleterun
from taskmanager.views import celerytest

urlpatterns = (
    # Examples:
    url(r'^runs/$', runs, name='runs'),
    url(r'^createrun/$', createrun, name='createrun'),
    url(r'^deleterun/$', deleterun, name='deleterun'),

    url(r'^celerytest/$', celerytest, name='celerytest'),
)
