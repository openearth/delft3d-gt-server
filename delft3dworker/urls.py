from django.conf.urls import include, url, handler404, handler500  # noqa

from rest_framework import routers

from delft3dworker import views


# REST Framework Router

router = routers.DefaultRouter()
router.register(r'groups', views.GroupViewSet, 'group')
router.register(r'versions', views.VersionViewSet, 'version')
router.register(r'scenarios', views.ScenarioViewSet, 'scenario')
router.register(r'scenes', views.SceneViewSet, 'scene')
router.register(r'searchforms', views.SearchFormViewSet, 'searchform')
router.register(r'templates', views.TemplateViewSet, 'template')
router.register(r'users', views.UserViewSet, 'user')
router.register(r'groupusagesummaries', views.GroupUsageSummaryViewSet, 'groupusagesummary')
router.register(r'userusagesummaries', views.UserUsageSummaryViewSet, 'userusagesummary')

# url patterns

urlpatterns = (
    url(r'^oidc/', include('mozilla_django_oidc.urls')),
    # REST Framework
    url(r'^api/v1/', include(router.urls)),
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),
    )
