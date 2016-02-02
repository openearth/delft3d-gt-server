from __future__ import absolute_import

import json
import uuid
import random

from django.core import serializers
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from delft3dworker.models import Delft3DWorker
from delft3dworker.tasks import rundocker

from delft3dgtmain.celery import app

COMPLETED = 'completed'
ERROR = 'error'
GET_NAME = 'name'
RUNNING = 'running'
SUCCESS = 'success'

def runs(request):

    for model in Delft3DWorker.objects.all():
        if model.status == RUNNING:
            model.progress += 1
            model.timeleft -= 4
            if model.progress == 100:
                model.status = COMPLETED
                model.timeleft = 0
            model.save()

    data = serializers.serialize('json', Delft3DWorker.objects.all())

    return HttpResponse(data, content_type = 'application/json; charset=utf8')


def createrun(request):

    msg_code = 'createresult'

    model = Delft3DWorker(
        name=request.GET.get(GET_NAME, 'none'),
        uuid=uuid.uuid4(),
        status=RUNNING,
        progress=0,
        timeleft=random.randint(123456, 1234567),
    )
    model.save()

    data = {
        'type': msg_code, 
        'id': str(model.uuid), 
        'status': {
            'code': SUCCESS, 
            'reason': ''
        }
    }

    return HttpResponse(json.dumps(data), content_type = 'application/json; charset=utf8')


def deleterun(request):

    msg_code = 'deleteresult'

    try:
        model = Delft3DWorker.objects.get(uuid=request.GET.get('uuid'))
        model.delete()

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


def celerytest(request):
    
    result = rundocker.delay('delft3d')
    
    return HttpResponse(json.dumps({'result':SUCCESS}), content_type = 'application/json; charset=utf8')


