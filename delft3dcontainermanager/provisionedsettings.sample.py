"""
Django provisionedsettings for delft3dcontainermanager app.

In here are all the settings which are dynamic on every
new provisioning run.
"""

BROKER_URL = 'redis://'
CELERY_RESULT_BACKEND = 'redis://'
