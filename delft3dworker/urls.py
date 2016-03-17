from django.conf.urls import include, url, handler404, handler500  # noqa

from delft3dworker.views import SceneCreateView
from delft3dworker.views import SceneDeleteView
from delft3dworker.views import SceneDetailView
from delft3dworker.views import SceneListView
from delft3dworker.views import SceneStartView


urlpatterns = (

    # namespaced urls
    url(r'^scene/create$', SceneCreateView.as_view(), name='scene_create'),
    url(r'^scene/delete$', SceneDeleteView.as_view(), name='scene_delete'),
    url(r'^scene/detail$', SceneDetailView.as_view(), name='scene_detail'),
    url(r'^scene/list$', SceneListView.as_view(), name='scene_list'),
    url(r'^scene/start$', SceneStartView.as_view(), name='scene_start'),

)
