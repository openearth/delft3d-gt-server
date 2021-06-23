"""
Django provisionedsettings for delft3dcontainermanager app.

In here are all the settings which are dynamic on every
new provisioning run.
"""

BROKER_URL = "redis://"
CELERY_RESULT_BACKEND = "redis://"
CELERY_ONCE = {
    "backend": "celery_once.backends.Redis",
    "settings": {"url": "redis://", "default_timeout": 60 * 60},
}
DOCKER_URL = "unix:///var/run/docker.sock"
