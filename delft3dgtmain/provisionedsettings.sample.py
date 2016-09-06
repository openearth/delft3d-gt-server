"""
Django provisionedsettings for delft3d project.

In here are all the settings which are dynamic on every
new provisioning run.
"""

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '<secret>'

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'djangodb',
        'USER': 'django',
        'PASSWORD': '<secret>',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# delft3dworker
DELFT3D_IMAGE_NAME = 'delft3d'
POSTPROCESS_IMAGE_NAME = 'python27_container'
PREPROCESS_IMAGE_NAME = 'python27_container'
PROCESS_IMAGE_NAME = 'python27_container'

# dummy workers
DELFT3D_DUMMY_IMAGE_NAME = 'dummy_simulation'
POSTPROCESS_DUMMY_IMAGE_NAME = 'dummy_postprocessing'
PREPROCESS_DUMMY_IMAGE_NAME = 'dummy_preprocessing'
PROCESS_DUMMY_IMAGE_NAME = 'dummy_processing'
EXPORT_DUMMY_IMAGE_NAME = 'dummy_export'

WORKER_FILEDIR = '/data/container/files'

BROKER_URL = 'redis://'
CELERY_RESULT_BACKEND = 'redis://'
