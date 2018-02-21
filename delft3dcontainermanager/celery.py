from __future__ import absolute_import

from __future__ import print_function
import os

from django.conf import settings
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'delft3dcontainermanager.settings')

app = Celery('delft3dgt')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.conf.ONCE = settings.CELERY_ONCE  # force CELERY_ONCE to load settings
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print(('Request: {0!r}'.format(self.request)))
