"""
Views for the ui.
"""
import os.path

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext


def handler403(request):
    filename = 'errorpages/403.html'

    styled_page = os.path.join(settings.STATIC_ROOT, '403.html')
    if os.path.isfile(styled_page):
        filename = styled_page

    r = render(request, filename,
        {}, context_instance=RequestContext(request))
    r.status_code = 403
    return r

def handler404(request):
    filename = 'errorpages/404.html'

    styled_page = os.path.join(settings.STATIC_ROOT, '404.html')
    if os.path.isfile(styled_page):
        filename = styled_page

    r = render(request, filename,
        {}, context_instance=RequestContext(request))
    r.status_code = 403
    return r
