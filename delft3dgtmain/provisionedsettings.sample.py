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

# versions
REPOS_URL = 'http://'
SVN_REV = '<revision number>'
DELFT3D_VERSION = 'Delft3D <version number>'
SVN_PRE_REV = '<revision number>'
SVN_PROC_REV = '<revision number>'
SVN_POST_REV = '<revision number>'
SVN_EXP_REV = '<revision number>'

# redis backend
BROKER_URL = 'redis://'
CELERY_RESULT_BACKEND = 'redis://'
CELERY_ONCE = {
  'backend': 'celery_once.backends.Redis',
  'settings': {
    'url': 'redis://',
    'default_timeout': 60 * 60
  }
}

BUCKETNAME = "s3bucket"
REQUIRE_REVIEW = False

# EMAIL backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
