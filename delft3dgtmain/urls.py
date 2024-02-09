"""delft3dgtmain URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.urls import include, path
from django.urls import re_path
from django.conf.urls.static import static
from django.contrib import admin

urlpatterns = [
    # Django Admin
    re_path(r"^admin/", admin.site.urls),
    # Delft3D-GT Worker API
    path("", include("delft3dworker.urls")),
    # Delft3D-GT Protected Services
    path("", include("delft3dgtprotectedservices.urls")),
    # Delft3D-GT Frontend
    path("", include("delft3dgtfrontend.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
