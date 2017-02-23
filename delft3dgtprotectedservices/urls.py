from django.conf.urls import url  # noqa

from delft3dgtprotectedservices import views

urlpatterns = (

    url(r'^files/(?P<simulation_uuid>[^/]*)/(?P<loc>.*)',
        views.files),

    url(r'^thredds/catalog.html',
        views.thredds_catalog),

    url(r'^thredds/catalog/files/catalog.html',
        views.thredds_catalog),

    url(r'^thredds/(?P<folder>[^/]*)/files/(?P<simulation_uuid>[^/]*)/(?P<loc>.*)',
        views.thredds),

    url(r'^thredds/(?P<loc>.*)',
        views.thredds_static),

)
