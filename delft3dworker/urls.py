from django.conf.urls import include, url, handler404, handler500  # noqa
from django.contrib.auth.decorators import login_required
from django.views.static import serve

from rest_framework import routers


from delft3dworker import views


# REST Framework Router

router = routers.DefaultRouter()
router.register(r'scenarios', views.ScenarioViewSet)
router.register(r'scenes', views.SceneViewSet)
router.register(r'templates', views.TemplateViewSet)

# url patterns

urlpatterns = (

    # REST Framework
    url(r'^api/v1/', include(router.urls)),
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),

    # DATA
    url(r'^data(?P<path>.*)$', login_required(serve), {
        'document_root': '/data/',
    }),

    # ###################################
    # The code below will be phased out in Sprint 4
    #

    # SCENARIO
    url(r'^scenario/create$', views.ScenarioCreateView.as_view(),
        name='scenario_create'),
    url(r'^scenario/delete$', views.ScenarioDeleteView.as_view(),
        name='scenario_delete'),
    url(r'^scenario/detail$', views.ScenarioDetailView.as_view(),
        name='scenario_detail'),
    url(r'^scenario/list$', views.ScenarioListView.as_view(),
        name='scenario_list'),
    url(r'^scenario/start$', views.ScenarioStartView.as_view(),
        name='scenario_start'),
    url(r'^scenario/stop$', views.ScenarioStopView.as_view(),
        name='scenario_stop'),

    # SCENE
    url(r'^scene/create$', views.SceneCreateView.as_view(),
        name='scene_create'),
    url(r'^scene/delete$', views.SceneDeleteView.as_view(),
        name='scene_delete'),
    url(r'^scene/detail$', views.SceneDetailView.as_view(),
        name='scene_detail'),
    url(r'^scene/export$', views.SceneExportView.as_view(),
        name='scene_export'),
    url(r'^scene/list$', views.SceneListView.as_view(),
        name='scene_list'),
    url(r'^scene/start$', views.SceneStartView.as_view(),
        name='scene_start'),
    url(r'^scene/stop$', views.SceneStopView.as_view(),
        name='scene_stop'),

    # TEMPLATE
    url(r'^scenario/template/detail$', views.TemplateDetailView.as_view(),
        name='template_detail'),
    url(r'^scenario/template/list$', views.TemplateListView.as_view(),
        name='template_list'),

)
