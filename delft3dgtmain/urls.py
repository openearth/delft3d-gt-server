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
from django.conf.urls import include
from django.conf.urls import url
from django.contrib import admin

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    # Django Admin
    url(r'^admin/',
        admin.site.urls),

    # Delft3D-GT Worker API
    url(r'^',
        include('delft3dworker.urls')),

    # Delft3D-GT Protected Services
    url(r'^',
        include('delft3dgtprotectedservices.urls')),

    # Delft3D-GT Frontend
    url(r'^',
        include('delft3dgtfrontend.urls')),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler403 = 'delft3dgtfrontend.views.handler403'
handler404 = 'delft3dgtfrontend.views.handler404'
