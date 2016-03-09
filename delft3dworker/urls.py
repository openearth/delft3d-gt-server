from django.conf.urls import include, url, handler404, handler500  # noqa
from delft3dworker.views import runs
from delft3dworker.views import createrun
from delft3dworker.views import deleterun
from delft3dworker.views import dorun
from delft3dworker.views import SceneCreateView, SceneDeleteView, SceneDetailView, SceneListView, SceneStartView

urlpatterns = (
    
    # Examples:
    url(r'^runs/$', runs, name='runs'),
    url(r'^createrun/$', createrun, name='createrun'),
    url(r'^deleterun/$', deleterun, name='deleterun'),
    url(r'^dorun/$', dorun, name='dorun'),

    # namespaced urls
    url(r'^scene/create$', SceneCreateView.as_view(), name='run_create'),
    url(r'^scene/delete/(?P<pk>\d*)$', SceneDeleteView.as_view(), name='run_delete'),
    url(r'^scene/detail/(?P<pk>\d*)$', SceneDetailView.as_view(), name='run_detail'),
    url(r'^scene/list$', SceneListView.as_view(), name='run_list'),
    url(r'^scene/start/(?P<pk>\d*)$', SceneStartView.as_view(), name='run_start'),

)
