from django.conf.urls import url  # noqa

from delft3dgtprotectedservices import views

urlpatterns = (

    url(r'^files/(?P<simulation_uuid>[^/]*)/(?P<loc>.*)',
        views.files),

    url(r'^thredds/catalog/files/(?P<simulation_uuid>[^/]*)/(?P<loc>.*)',
        views.thredds),

    url(r'^thredds/(?P<loc>.*)',
        views.thredds_static),

)
