"""
Django settings for delft3d project.

Generated by 'django-admin startproject' using Django 1.9.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os
import sys

from datetime import timedelta
from kubernetes import config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'django_filters',
    'crispy_forms',
    'guardian',
    'constance',
    'constance.backends.database',

    'delft3dcontainermanager',
    'delft3dworker',
    'delft3dgtfrontend',
    'delft3dgtprotectedservices',
]

CONSTANCE_CONFIG = {
    'MAX_SIMULATIONS': (2, "Max simulations that can run in Amazon."),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'delft3dgtmain.urls'

# Object permissions

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # default
    'guardian.backends.ObjectPermissionBackend',
]

ANONYMOUS_USER_NAME = None  # No anon user

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_ROOT = '/opt/delft3d-gt/static/'
STATIC_URL = '/static/'
STATICFILES_DIRS = ['/opt/delft3d-gt/delft3d-gt-ui/dist/']

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [STATIC_ROOT],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'delft3dgtmain.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation'
        '.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation'
        '.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation'
        '.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation'
        '.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Login
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# ######
# Celery
# ######

# Disabling rate limits altogether is recommended if you don't have any tasks
# using them. This is because the rate limit subsystem introduces quite a lot
# of complexity.
CELERY_DISABLE_RATE_LIMITS = True

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TRACK_STARTED = True  # All pending tasks can be revoked
CELERY_TASK_PUBLISH_RETRY = False  # No retry on connection error
CELERY_MESSAGE_COMPRESSION = 'gzip'  # Can help on docker inspect messages

# Custom task expire time
TASK_EXPIRE_TIME = 5 * 60  # After 5 minutes, tasks are forgotten
CELERY_TASK_RESULT_EXPIRES = 5 * 60  # After 5 minutes redis keys are deleted

# Worker specific settings, becomes important
# with cloud workers, when there are multiple
# workers for each queue.
CELERY_ACKS_LATE = False
CELERYD_PREFETCH_MULTIPLIER = 1

# Celerybeat
CELERY_BEAT_SCHEDULE = {
    'sync_kube_cluster': {
        'task': 'delft3dcontainermanager.tasks.delft3dgt_kube_pulse',
        'schedule': timedelta(seconds=15),
        'options': {'queue': 'beat', 'expires': TASK_EXPIRE_TIME}
    },
    # 'latest_svn': {
    #     'task': 'delft3dcontainermanager.tasks.delft3dgt_latest_svn',
    #     'schedule': timedelta(hours=6),
    #     'options': {'queue': 'beat', 'expires': TASK_EXPIRE_TIME}
    # },
}

WORKER_FILEURL = '/files'


# REST Framework

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'delft3dworker.authentication.CsrfExemptSessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'rest_framework.permissions.DjangoModelPermissions',
        # 'delft3dworker.permissions.ViewObjectPermissions',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        # 'rest_framework.filters.DjangoFilterBackend',
        'django_filters.rest_framework.DjangoFilterBackend',
        # 'django_filters.rest_framework.FilterSet',
        # 'rest_framework.filters.SearchFilter',
        # 'rest_framework.filters.DjangoObjectPermissionsFilter',
    ]
}

# try to load kubectl config
try:
    config.load_kube_config()
except IOError:
    print("Can't load kubernetes config!")

# import provisioned settings
try:
    from provisionedsettings import *
except ImportError:
    print("Failed to import provisioned settings!")
    SECRET_KEY = 'test'

# TESTING

if 'test' in sys.argv:

    from celery import Celery
    import logging
    logging.disable(logging.CRITICAL)

    if 'TRAVIS' in os.environ:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'travis_ci_test',
                'USER': 'postgres',
                'HOST': 'localhost',
                'PORT': '5432',
            }
        }
    else:
        DATABASES['default'].update({'NAME': 'djangodb_test'})

    # Debug on running tests
    DEBUG = True

    # use a subdir for testing output
    WORKER_FILEDIR = 'test/'

    CELERY_ONCE = {
      'backend': 'celery_once.backends.Redis',
      'settings': {
        'url': 'redis://127.0.0.1:6379/0',
        'default_timeout': 60 * 60
      }
    }

    # make sure celery delayed tasks are executed immediately
    CELERY_RESULT_BACKEND = 'cache'
    CELERY_CACHE_BACKEND = 'memory'
    TASK_EXPIRE_TIME = 24 * 60 * 60  # Expire after a day
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True  # Issue #75

    app = Celery('delft3dgt')
    app.conf.CELERY_ALWAYS_EAGER = True
    app.conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    app.conf.ONCE = CELERY_ONCE

    # set dummy container image names to dummy images
    DELFT3D_DUMMY_IMAGE_NAME = 'dummy_simulation'
    POSTPROCESS_DUMMY_IMAGE_NAME = 'dummy_postprocessing'
    PREPROCESS_DUMMY_IMAGE_NAME = 'dummy_preprocessing'
    PROCESS_DUMMY_IMAGE_NAME = 'dummy_processing'
    EXPORT_DUMMY_IMAGE_NAME = 'dummy_export'
    SYNC_CLEANUP_IMAGE_NAME = 'dummy_sync'

    # set container image names to dummy images
    DELFT3D_IMAGE_NAME = 'dummy_simulation'
    POSTPROCESS_IMAGE_NAME = 'dummy_postprocessing'
    PREPROCESS_IMAGE_NAME = 'dummy_preprocessing'
    PROCESS_IMAGE_NAME = 'dummy_processing'
    EXPORT_IMAGE_NAME = 'dummy_export'

    # versions
    REPOS_URL = 'http://example.com/repos'
    SVN_REV = '123'
    SVN_PRE_REV = '124'
    SVN_PROC_REV = '125'
    SVN_POST_REV = '126'
    SVN_EXP_REV = '127'
    DELFT3D_VERSION = 'Delft3D version 123456'

    # max number of simulations
    MAX_SIMULATIONS = 1
    REQUIRE_REVIEW = False
    BUCKETNAME = ""

    # Docker URL this setting is from the delf3dcontainermanger app
    DOCKER_URL = 'unix:///var/run/docker.sock'
