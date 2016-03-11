from __future__ import absolute_import

from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import View

from json_views.views import JSONDetailView
from json_views.views import JSONListView

from delft3dworker.models import Scene


# ################################### Sprint 2 Architecture

class SceneCreateView(CreateView):    
    model = Scene
    fields = ['name', 'state', 'info']
    success_url = reverse_lazy('scene_list')


class SceneDeleteView(DeleteView):    
    model = Scene
    success_url = reverse_lazy('scene_list')


class SceneDetailView(JSONDetailView):    
    model = Scene


class SceneListView(JSONListView):    
    model = Scene


class SceneStartView(View):    
    model = Scene

    # TODO: remove get
    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        scene = get_object_or_404(Scene, pk=pk)
        return HttpResponse(scene.simulate())

    def post(self, request, *args, **kwargs):
        pk = kwargs['pk']
        scene = get_object_or_404(Scene, pk=pk)
        return HttpResponse(scene.simulate())




# ################################### Sprint 1 Architecture
import json
import uuid
import random

from celery.result import AsyncResult
from celery.contrib.abortable import AbortableAsyncResult

from django.conf import settings
from django.core import serializers
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from delft3dgtmain.celery import app
from delft3dworker.models import Delft3DWorker
from delft3dworker.models import SimulationTask

from delft3dworker.tasks import rundocker


# GET keys
GET_KEY_NAME = 'name'
GET_KEY_UUID = 'uuid'
GET_KEY_DT = 'dt'

# msg codes
COMPLETED = 'completed'
ERROR = 'error'
RUNNING = 'running'
SUCCESS = 'success'


def runs(request):

    workers = Delft3DWorker.objects.all()

    # update worker task info in model
    for worker in workers:
        worker.info = AsyncResult(worker.workerid).info

    data = serializers.serialize('json', workers)

    return HttpResponse(data.replace("u'", "'"), content_type = 'application/json; charset=utf8')


def createrun(request):
    msg_code = 'createresult'
    
    model = Delft3DWorker(
        name=request.GET.get(GET_KEY_NAME, 'none'),
        uuid=uuid.uuid4(),
        status=RUNNING,
        json = '{ "dt": ' + request.GET.get(GET_KEY_DT, '1') + ' }'
    )
    model.save()
    
    data = {
        'type': msg_code, 
        'uuid': str(model.uuid), 
        'status': {
            'code': SUCCESS, 
            'reason': ''
        }
    }

    return HttpResponse(json.dumps(data), content_type = 'application/json; charset=utf8')


def deleterun(request):
    msg_code = 'deleteresult'

    try:

        delft3d_worker = Delft3DWorker.objects.get(uuid=request.GET.get('uuid'))

        # app.control.revoke(delft3d_worker.workerid)
        result = AbortableAsyncResult(delft3d_worker.workerid)

        result.abort()

        result.get()        
        
        delft3d_worker.delete()

        data = {
            'type': msg_code, 
            'status': {
                'code': SUCCESS, 
                'reason': ''
            }
        }

    except Delft3DWorker.DoesNotExist, Argument:
        
        data = {
            'type': msg_code, 
            'status': {
                'code': ERROR, 
                'reason': str(Argument)
            }
        }

    return HttpResponse(json.dumps(data), content_type = 'application/json; charset=utf8')


def dorun(request):
    msg_code = 'doresult'

    try:
        get_uuid = request.GET.get(GET_KEY_UUID, 'none')
        delft3d_worker = get_object_or_404(Delft3DWorker, uuid=get_uuid)
        
        result = rundocker.delay(settings.DELFT3D_IMAGE_NAME, delft3d_worker.uuid, delft3d_worker.workingdir)
        
        delft3d_worker.workerid = result.id
        delft3d_worker.save()

        data = {
            'type': msg_code, 
            'status': {
                'code': SUCCESS, 
                'reason': ''
            }
        }
    except Delft3DWorker.DoesNotExist, Argument:
        data = {
            'type': msg_code, 
            'status': {
                'code': ERROR, 
                'reason': str(Argument)
            }
        }

    return HttpResponse(json.dumps(data), content_type = 'application/json; charset=utf8')
