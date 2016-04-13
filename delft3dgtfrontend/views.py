"""
Views for the ui.
"""
from __future__ import absolute_import
import io
import zipfile

from django.http import HttpResponse


def export(request, scene, selection):
    """export data into a zip file
    - scene: model run
    - selection: images or log
    """

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
