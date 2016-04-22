"""
Views for the ui.
"""
from __future__ import absolute_import

import io
import json
import os
import zipfile

from datetime import datetime

from django.core.urlresolvers import reverse_lazy
from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import View


from json_views.views import JSONDetailView
from json_views.views import JSONListView

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import Template


# ################################### SCENARIO

class ScenarioCreateView(View):
    model = Scenario

    def post(self, request, *args, **kwargs):

        # dummy stub code for front-end to integrate

        name = datetime.now()

        newscenario = Scenario(name='Scenario {}'.format(name))
        newscenario.save()

        scene1 = Scene(name="Scene {}".format(name), scenario=newscenario)
        scene1.save()
        scene2 = Scene(name="Scene {}".format(name), scenario=newscenario)
        scene2.save()

        return JsonResponse({'created':'ok'})

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ScenarioCreateView, self).dispatch(*args, **kwargs)


class ScenarioDeleteView(DeleteView):
    model = Scenario

    def get_object(self):
        scenario_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        return Scenario.objects.get(id=scenario_id)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        payload = {'status': 'deleted'}
        return JsonResponse(payload)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ScenarioDeleteView, self).dispatch(*args, **kwargs)


class ScenarioDetailView(JSONDetailView):
    model = Scenario

    def get_object(self):
        scenario_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        scenario = Scenario.objects.get(id=scenario_id)
        return scenario

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ScenarioDetailView, self).dispatch(*args, **kwargs)


class ScenarioListView(JSONListView):
    model = Scenario

    def get_queryset(self):
        queryset = Scenario.objects.all().order_by('id')
        return queryset

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ScenarioListView, self).dispatch(*args, **kwargs)


class ScenarioStartView(View):
    model = Scenario

    # TODO: remove get
    def get(self, request, *args, **kwargs):
        scenario_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        scenario = get_object_or_404(Scenario, id=scenario_id)
        payload = {'status': scenario.start()}
        return JsonResponse(payload)

    def post(self, request, *args, **kwargs):
        scenario_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        scenario = get_object_or_404(Scenario, id=scenario_id)
        payload = {'status': scenario.start()}
        return JsonResponse(payload)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ScenarioStartView, self).dispatch(*args, **kwargs)


# ################################### SCENE

class SceneCreateView(CreateView):
    model = Scene
    fields = ['name', 'state', 'info']

    def post(self, request, *args, **kwargs):
        return super(SceneCreateView, self).post(request, *args, **kwargs)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(SceneCreateView, self).dispatch(*args, **kwargs)


class SceneDeleteView(DeleteView):
    model = Scene

    def get_object(self):
        scene_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        return Scene.objects.get(id=scene_id)

    def delete(self, request, *args, **kwargs):
        deletefiles = (request.GET.get('delete_files') or request.POST.get('delete_files'))
        self.object = self.get_object()
        self.object.abort()
        payload = {'status': 'deleted', 'files_deleted': deletefiles}
        return JsonResponse(payload)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(SceneDeleteView, self).dispatch(*args, **kwargs)


class SceneDetailView(JSONDetailView):
    model = Scene

    def get_object(self):
        scene_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        scene = Scene.objects.get(id=scene_id)
        scene.update_state()
        return scene

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(SceneDetailView, self).dispatch(*args, **kwargs)


class SceneListView(JSONListView):
    model = Scene

    def get_queryset(self):
        queryset = Scene.objects.all().order_by('id')
        for scene in queryset.iterator():
            scene.update_state()
        return queryset

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(SceneListView, self).dispatch(*args, **kwargs)


class SceneStartView(View):
    model = Scene

    # TODO: remove get
    def get(self, request, *args, **kwargs):
        scene_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        scene = get_object_or_404(Scene, id=scene_id)
        payload = {'status': scene.start()}
        return JsonResponse(payload)

    def post(self, request, *args, **kwargs):
        scene_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        scene = get_object_or_404(Scene, id=scene_id)
        payload = {'status': scene.start()}

        print '------------------------------------------------------------------------ SceneStartView {}'.format(scene_id)

        return JsonResponse(payload)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(SceneStartView, self).dispatch(*args, **kwargs)


class SceneExportView(View):
    model = Scene

    def get(self, request, *args, **kwargs):
        """export data into a zip file
        - scene: model run
        - selection: images or log
        """
        scene_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        scene = get_object_or_404(Scene, id=scene_id)

        # we might need to move this to worker if:
        # - we need to do this in the background (in a task)

        # Alternatives to this implementation are:
        # - django-zip-view (sets mimetype and content-disposition)
        # - django-filebrowser (filtering and more elegant browsing)

        # from: http://stackoverflow.com/questions/67454/serving-dynamically-generated-zip-archives-in-django

        zip_filename = 'export.zip'

        # Open BytesIO to grab in-memory ZIP contents
        # (be explicit about bytes)
        stream = io.BytesIO()

        # The zip compressor
        zf = zipfile.ZipFile(stream, "w")

        # Add files here.
        # If you run out of memory you have 2 options:
        # - stream
        # - zip in a subprocess shell with zip
        # - zip to temporary file
        for root, dirs, files in os.walk(scene.workingdir):
            for f in files:
                if f.endswith('.png'):  # Could be dynamic or tuple of extensions
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, scene.workingdir)
                    zf.write(abs_path, rel_path)

        # Must close zip for all contents to be written
        zf.close()

        # Grab ZIP file from in-memory, make response with correct MIME-type
        resp = HttpResponse(
            # rewinds and gets bytes
            stream.getvalue(),
            # urls don't use extensions but mime types
            content_type="application/x-zip-compressed"
        )
        # ..and correct content-disposition
        resp['Content-Disposition'] = 'attachment; filename=%s' % zip_filename

        # TODO create a test with a django request and test if the file can be read
        return resp

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(SceneExportView, self).dispatch(*args, **kwargs)


# ################################### TEMPLATE

class TemplateDetailView(JSONDetailView):
    model = Template

    def get_object(self):
        template_id = (self.request.GET.get('id') or self.request.POST.get('id'))
        template = Template.objects.get(id=template_id)
        return template

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(TemplateDetailView, self).dispatch(*args, **kwargs)


class TemplateListView(JSONListView):
    model = Template

    def get_queryset(self):
        queryset = Template.objects.all().order_by('id')
        return queryset

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(TemplateListView, self).dispatch(*args, **kwargs)
