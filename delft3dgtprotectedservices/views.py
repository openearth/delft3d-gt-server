from uuid import UUID

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from delft3dworker.models import Scene


@login_required
def files(request, simulation_uuid, loc):

    # try UUID or 404
    try:
        uuid = UUID(simulation_uuid)
    except ValueError:
        return HttpResponse(status=404)

    # get scene or 404
    scene = get_object_or_404(Scene, suid=uuid)

    # return 403 if not allowed
    if not request.user.has_perm("view_scene", scene):
        return HttpResponse(status=403)

    # redirect to nginx protected files
    response = HttpResponse()
    response["X-Accel-Redirect"] = "/protected_files/{0}/{1}".format(
        simulation_uuid, loc)

    return response


@login_required
def thredds(request, simulation_uuid, loc):

    # try UUID or 404
    try:
        uuid = UUID(simulation_uuid)
    except ValueError:
        return HttpResponse(status=404)

    # get scene or 404
    scene = get_object_or_404(Scene, suid=uuid)

    # return 403 if not allowed
    if not request.user.has_perm("view_scene", scene):
        return HttpResponse(status=403)

    # redirect to nginx thredds
    response = HttpResponse()
    response["X-Accel-Redirect"] = (
        "/protected_thredds/catalog/files/{0}/{1}?{2}"
    ).format(simulation_uuid, loc, request.GET.urlencode())

    return response


@login_required
def thredds_static(request, loc):

    # redirect to nginx thredds
    response = HttpResponse()
    response["X-Accel-Redirect"] = "/protected_thredds/{0}".format(loc)

    return response
