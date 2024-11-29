from __future__ import absolute_import

from django.urls import re_path  # noqa

from delft3dgtprotectedservices import views

urlpatterns = (
    re_path(r"^files/(?P<simulation_uuid>[^/]*)/(?P<loc>.*)", views.files),
    re_path(r"^thredds/catalog.html", views.thredds_catalog),
    re_path(r"^thredds/catalog/files/catalog.html", views.thredds_catalog),
    re_path(
        r"^thredds/(?P<folder>[^/]*)/files/(?P<simulation_uuid>[^/]*)/(?P<loc>.*)",
        views.thredds,
    ),
    re_path(r"^thredds/(?P<loc>.*)", views.thredds_static),
)
