from __future__ import absolute_import
import os
from ddtrace import patch_all
patch_all()
from celery import Celery
from django.conf import settings  # noqa

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'delft3dgtmain.settings')

app = Celery('delft3dgt')

app.conf.ONCE = settings.CELERY_ONCE  # force CELERY_ONCE to load settings

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
