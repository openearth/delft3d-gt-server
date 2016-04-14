"""
Views for the ui.
"""
from __future__ import absolute_import

import io
import zipfile

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

from delft3dworker.models import Scene


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
        self.object = self.get_object()
        self.object.delete()
        payload = {'status': 'deleted'}
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

        # we might need to move this to worker if:
        # - we need info of the scenes
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
