from __future__ import absolute_import

import base64
import os
from uuid import UUID

from django.contrib.auth import authenticate, login
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

    loc_path, loc_extension = os.path.splitext(loc)

    # redirect to nginx protected files
    response = HttpResponse()
    response["X-Accel-Redirect"] = "/protected_files/{0}/{1}".format(
        simulation_uuid, loc
    )

    # All users are allowed to view png images
    if request.user.has_perm("view_scene", scene) and loc_extension == ".png":
        return response

    # User with extended view permissions is allowed to view all files
    if request.user.has_perm("extended_view_scene", scene):
        return response

    # Else return 403
    else:
        return HttpResponse(status=403)


@login_required
def thredds_catalog(request):

    if not request.user.is_superuser:
        return HttpResponse(status=403)

    # redirect to nginx thredds
    response = HttpResponse()
    response["X-Accel-Redirect"] = "/protected_thredds/catalog/files/catalog.html"

    return response


def thredds(request, folder, simulation_uuid, loc):

    # try UUID or 404
    try:
        uuid = UUID(simulation_uuid)
    except ValueError:
        return HttpResponse(status=404)

    # get scene or 404
    scene = get_object_or_404(Scene, suid=uuid)

    # Check for basic auth info and log user in
    if "authorization" in request.headers:
        auth = request.headers["authorization"].split()
        if len(auth) == 2:
            if auth[0].lower() == "basic":
                decoded_auth = base64.b64decode(auth[1])
                uname, passwd = decoded_auth.decode("utf-8").split(":")
                user = authenticate(username=uname, password=passwd)
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        request.user = user

    # return 403 if not allowed
    if request.user.has_perm("extended_view_scene", scene):

        # redirect to nginx thredds
        response = HttpResponse()
        response["X-Accel-Redirect"] = (
            "/protected_thredds/{0}/files/{1}/{2}?{3}"
        ).format(folder, simulation_uuid, loc, request.META.get("QUERY_STRING", ""))
        return response

    else:
        return HttpResponse(status=403)


def thredds_static(request, loc):

    # Check for basic auth info and log user in
    if "authorization" in request.headers:
        auth = request.headers["authorization"].split()
        if len(auth) == 2:
            if auth[0].lower() == "basic":
                uname, passwd = base64.b64decode(auth[1]).split(":")
                user = authenticate(username=uname, password=passwd)
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        request.user = user

    if not request.user.is_authenticated:
        return HttpResponse(status=403)

    # redirect to nginx thredds
    response = HttpResponse()
    response["X-Accel-Redirect"] = ("/protected_thredds/{0}?{1}").format(
        loc, request.META.get("QUERY_STRING", "")
    )

    return response
