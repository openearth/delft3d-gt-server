from django.conf.urls import include, url, handler404, handler500  # noqa

from delft3dworker.views import runs
from delft3dworker.views import createrun
from delft3dworker.views import deleterun
from delft3dworker.views import dorun
from delft3dworker.views import SceneCreateView, SceneDeleteView, SceneDetailView, SceneListView, SceneStartView


urlpatterns = (

    # Sprint 1 Architecture
    url(r'^runs/$', runs, name='runs'),
    url(r'^createrun/$', createrun, name='createrun'),
    url(r'^deleterun/$', deleterun, name='deleterun'),
    url(r'^dorun/$', dorun, name='dorun'),

    # namespaced urls, Sprint 2 Architecture
    url(r'^scene/create$', SceneCreateView.as_view(), name='scene_create'),
    url(r'^scene/delete$', SceneDeleteView.as_view(), name='scene_delete'),
    url(r'^scene/detail$', SceneDetailView.as_view(), name='scene_detail'),
    url(r'^scene/list$', SceneListView.as_view(), name='scene_list'),
    url(r'^scene/start$', SceneStartView.as_view(), name='scene_start'),

)
