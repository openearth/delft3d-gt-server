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

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_ROOT = '/opt/delft3d-gt/static/'

# delft3dworker
DELFT3D_IMAGE_NAME = 'delft3d'
WORKER_FILEDIR = '/files'
