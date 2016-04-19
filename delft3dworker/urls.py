from django.conf.urls import include, url, handler404, handler500  # noqa

from delft3dworker.views import ScenarioCreateView
from delft3dworker.views import ScenarioDeleteView
from delft3dworker.views import ScenarioDetailView
from delft3dworker.views import ScenarioListView
from delft3dworker.views import ScenarioStartView
from delft3dworker.views import SceneCreateView
from delft3dworker.views import SceneDeleteView
from delft3dworker.views import SceneDetailView
from delft3dworker.views import SceneExportView
from delft3dworker.views import SceneListView
from delft3dworker.views import SceneStartView
from delft3dworker.views import TemplateDetailView
from delft3dworker.views import TemplateListView

from django.contrib.auth.decorators import login_required
from django.views.static import serve


urlpatterns = (

    # SCENARIO
    url(r'^scenario/create$', ScenarioCreateView.as_view(), name='scenario_create'),
    url(r'^scenario/delete$', ScenarioDeleteView.as_view(), name='scenario_delete'),
    url(r'^scenario/detail$', ScenarioDetailView.as_view(), name='scenario_detail'),
    url(r'^scenario/list$', ScenarioListView.as_view(), name='scenario_list'),
    url(r'^scenario/start$', ScenarioStartView.as_view(), name='scenario_start'),

    # TEMPLATE
    url(r'^/scenario/template/detail$', TemplateDetailView.as_view(), name='template_detail'),
    url(r'^/scenario/template/list$', TemplateListView.as_view(), name='template_list'),

    # SCENE
    url(r'^scene/create$', SceneCreateView.as_view(), name='scene_create'),
    url(r'^scene/delete$', SceneDeleteView.as_view(), name='scene_delete'),
    url(r'^scene/detail$', SceneDetailView.as_view(), name='scene_detail'),
    url(r'^scene/export$', SceneExportView.as_view(), name='scene_export'),
    url(r'^scene/list$', SceneListView.as_view(), name='scene_list'),
    url(r'^scene/start$', SceneStartView.as_view(), name='scene_start'),

    # DATA
    url(r'^data(?P<path>.*)$', login_required(serve), {
        'document_root': '/data/',
    }),
)
