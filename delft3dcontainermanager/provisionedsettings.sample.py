"""
Django provisionedsettings for delft3dcontainermanager app.

In here are all the settings which are dynamic on every
new provisioning run.
"""

BROKER_URL = 'redis://'
CELERY_RESULT_BACKEND = 'redis://'
ONCE_REDIS_URL = 'redis://'

DOCKER_URL = 'unix:///var/run/docker.sock'