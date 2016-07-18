"""
Views for the ui.
"""
from __future__ import absolute_import

import django_filters
import json
import logging

from datetime import datetime

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import View

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_objects_for_user
from guardian.decorators import permission_required_or_403
from json_views.views import JSONDetailView
from json_views.views import JSONListView

from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import detail_route
from rest_framework.decorators import list_route
from rest_framework.response import Response

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import Template
from delft3dworker.models import SearchForm
from delft3dworker.permissions import ViewObjectPermissions
from delft3dworker.serializers import GroupSerializer
from delft3dworker.serializers import ScenarioSerializer
from delft3dworker.serializers import SceneSerializer
from delft3dworker.serializers import SearchFormSerializer
from delft3dworker.serializers import TemplateSerializer
from delft3dworker.serializers import UserSerializer


# ################################### REST


# ### ViewSets

class ScenarioViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows scenarios to be viewed or edited.
    """
    serializer_class = ScenarioSerializer
    filter_backends = (
        filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        filters.DjangoObjectPermissionsFilter,
    )
    permission_classes = (permissions.IsAuthenticated,
                          ViewObjectPermissions,)

    # Default ordering by id, so latest run is last in list
    # reverse by setting ('-id',)
    ordering = ('id',)

    # Our own custom filter to create custom search fields
    # this creates &name= among others
    filter_backends = (filters.SearchFilter,)
    search_fields = ('$name', )

    queryset = Scenario.objects.none()

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given parameter,
        by filtering against a `parameter` query parameter in the URL.

        Possible values:
            # filters on key occurance
            - parameter="parameter
            # filters on key occurance and value
            - parameter="parameter,value"
            # filters on key occurance and value between min & max
            - parameter="parameter,minvalue,maxvalue"
        """
        queryset = Scenario.objects.all()

        # Filter on parameter
        parameters = self.request.query_params.getlist('parameter', [])
        template = self.request.query_params.getlist('template', [])

        if len(parameters) > 0:
            # Processing user input
            # will sometimes fail
            try:
                for parameter in parameters:

                    p = parameter.split(',')

                    # Key exist lookup
                    if len(p) == 1:

                        key = parameter
                        logging.info("Lookup parameter {}".format(key))
                        queryset = queryset.filter(parameters__icontains=key)

                    # Key, value lookup
                    elif len(p) == 2:

                        key, value = p
                        logging.info(
                            "Lookup value for parameter {}".format(key))

                        # Find integers or floats
                        try:
                            value = float(value)
                        except ValueError:
                            pass  # no float? no problem

                        # Create json lookup
                        # q = {key: {'value': value}}

                        # Not yet possible to do json queries directly
                        # Requires JSONField from Postgresql 9.4 and Django 1.9
                        # So we loop manually (bad performance!)
                        wanted = []
                        queryset = queryset.filter(parameters__icontains=key)
                        for scenario in queryset:
                            for pval in scenario.parameters[key].get(
                                    'values', []):
                                if value == pval:
                                    wanted.append(scenario.id)

                        queryset = queryset.filter(pk__in=wanted)

                    # Key, min, max lookup
                    elif len(p) == 3:

                        key, minvalue, maxvalue = p
                        logging.info(
                            "Lookup value [{} - {}] for parameter {}".format(
                                minvalue,
                                maxvalue,
                                key
                            )
                        )

                        # Make into integers or floats
                        # (no float values should throw exception)
                        minvalue = float(minvalue)
                        maxvalue = float(maxvalue)

                        # Create json lookup
                        # q = {key: {'value': value}}

                        # Not yet possible to do json queries directly
                        # Requires JSONField from Postgresql 9.4 and Django 1.9
                        # So we loop manually (bad performance!)
                        wanted = []
                        queryset = queryset.filter(parameters__icontains=key)
                        for scenario in queryset:
                            for pval in scenario.parameters[key].get(
                                    'values', []):
                                if minvalue <= pval <= maxvalue:
                                    wanted.append(scenario.id)

                        queryset = queryset.filter(pk__in=wanted)

            except Exception as e:
                logging.exception(
                    "Search with params {} and template {} failed".format(
                        parameters, template)
                )
                return Scene.objects.none()

        if len(template) > 0:
            queryset = queryset.filter(template__name__in=template)

        return queryset

    def perform_create(self, serializer):
        if serializer.is_valid():
            instance = serializer.save()
            instance.owner = self.request.user

            # Inspect validated field data.
            parameters = serializer.validated_data['parameters'] if (
                'parameters' in serializer.validated_data
            ) else None

            if parameters:
                instance.load_settings(parameters)
                instance.createscenes(self.request.user)

            assign_perm('add_scenario', self.request.user, instance)
            assign_perm('change_scenario', self.request.user, instance)
            assign_perm('delete_scenario', self.request.user, instance)
            assign_perm('view_scenario', self.request.user, instance)

            instance.save()

            # 25 april '16: Almar, Fedor & Tijn decided that
            # a scenario should be started server-side after creation
            instance.start(instance.owner)

    # Pass on user to check permissions
    def perform_destroy(self, instance):
        instance.delete(self.request.user)

    @detail_route(methods=["put"])  # denied after publish to company/world
    def start(self, request, pk=None):
        scenario = self.get_object()

        if "workflow" in request.data:
            scenario.start(request.user, workflow=request.data["workflow"])
        else:
            scenario.start(request.user, workflow="main")

        serializer = self.get_serializer(scenario)

        return Response(serializer.data)

    @detail_route(methods=["put"])  # denied after publish to company/world
    def stop(self, request, pk=None):
        scenario = self.get_object()

        scenario.abort()

        serializer = self.get_serializer(scenario)

        return Response(serializer.data)

    @detail_route(methods=["post"])  # denied after publish to world
    def publish_company(self, request, pk=None):
        self.get_object().publish_company(request.user)
        return Response({'status': 'Published scenario to company'})

    @detail_route(methods=["post"])  # denied after publish to world
    def publish_world(self, request, pk=None):
        self.get_object().publish_world(request.user)
        return Response({'status': 'Published scenario to world'})


class SceneViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows scenes to be viewed or edited.
    """
    serializer_class = SceneSerializer
    filter_backends = (
        filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        filters.DjangoObjectPermissionsFilter,
    )
    # Default order by name, so runs don't jump around
    ordering = ('id',)

    # Searchfilter backend for field &search=
    filter_backends = (filters.SearchFilter,)
    search_fields = ('$name', )

    # Permissions backend which we could use in filter
    permission_classes = (permissions.IsAuthenticated,
                          ViewObjectPermissions,)

    # If we overwrite get queryset
    queryset = Scene.objects.none()

    def perform_create(self, serializer):
        if serializer.is_valid():
            instance = serializer.save()
            instance.owner = self.request.user
            instance.shared = "p"  # private
            instance.save()

            assign_perm('view_scene', self.request.user, instance)
            assign_perm('add_scene', self.request.user, instance)
            assign_perm('change_scene', self.request.user, instance)
            assign_perm('delete_scene', self.request.user, instance)

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given parameter,
        by filtering against a `parameter` query parameter in the URL.

        Possible values:
            # filters on key occurance
            - parameter="parameter
            # filters on key occurance and value
            - parameter="parameter,value"
            # filters on key occurance and value between min & max
            - parameter="parameter,minvalue,maxvalue"
        """
        queryset = Scene.objects.all()
        # self.queryset = queryset

        # Filter on parameter
        parameters = self.request.query_params.getlist('parameter', [])
        template = self.request.query_params.getlist('template', [])
        shared = self.request.query_params.getlist('shared', [])

        if len(parameters) > 0:
            # Processing user input
            # will sometimes fail
            try:
                for parameter in parameters:

                    p = parameter.split(',')

                    # Key exist lookup
                    if len(p) == 1:

                        key = parameter
                        logging.info("Lookup parameter {}".format(key))
                        queryset = queryset.filter(parameters__icontains=key)

                    # Key, value lookup
                    elif len(p) == 2:

                        key, value = p
                        logging.info(
                            "Lookup value for parameter {}".format(key))

                        # Find integers or floats
                        try:
                            value = float(value)
                        except:
                            # could filter on string such as parameter = engine
                            pass

                        # Create json lookup
                        # q = {key: {'value': value}}

                        # Not yet possible to do json queries directly
                        # Requires JSONField from Postgresql 9.4 and Django 1.9
                        # So we loop manually (bad performance!)
                        wanted = []
                        queryset = queryset.filter(parameters__icontains=key)

                        for scene in queryset:
                            if scene.parameters[key]['value'] == value:
                                wanted.append(scene.id)

                        queryset = queryset.filter(pk__in=wanted)

                    # Key, min, max lookup
                    elif len(p) == 3:

                        key, minvalue, maxvalue = p
                        logging.info(
                            "Lookup value [{} - {}] for parameter {}".format(
                                minvalue,
                                maxvalue,
                                key
                            )
                        )

                        # Find integers or floats
                        minvalue = float(minvalue)
                        maxvalue = float(maxvalue)

                        # Create json lookup
                        # q = {key: {'value': value}}

                        # Not yet possible to do json queries directly
                        # Requires JSONField from Postgresql 9.4 and Django 1.9
                        # So we loop manually (bad performance!)
                        wanted = []
                        queryset = queryset.filter(parameters__icontains=key)

                        for scene in queryset:
                            values = scene.parameters[key]['value']
                            if minvalue <= values <= maxvalue:

                                wanted.append(scene.id)

                        queryset = queryset.filter(pk__in=wanted)

            except Exception as e:
                logging.exception(
                    "Search with params {} and template {} failed".format(
                        parameters, template)
                )
                return Scene.objects.none()

        if len(template) > 0:
            queryset = queryset.filter(scenario__template__name__in=template)

        if len(shared) > 0:
            lookup = {"private": "p", "company": "c", "public": "w"}
            wanted = [lookup[share] for share in shared if share in lookup]
            queryset = queryset.filter(shared__in=wanted)

        # self.queryset = queryset

        return queryset

    @detail_route(methods=["put"])  # denied after publish to company/world
    def start(self, request, pk=None):
        scene = self.get_object()

        if "workflow" in request.data:
            scene.start(workflow=request.data["workflow"])
        else:
            scene.start(workflow="main")

        serializer = self.get_serializer(scene)

        return Response(serializer.data)

    @detail_route(methods=["put"])  # denied after publish to company/world
    def stop(self, request, pk=None):
        scene = self.get_object()

        scene.abort()

        serializer = self.get_serializer(scene)

        return Response(serializer.data)

    @detail_route(methods=["post"])  # denied after publish to world
    def publish_company(self, request, pk=None):
        published = self.get_object().publish_company(request.user)

        if not published:
            return Response(
                {'status': 'Something went wrong publishing scene to company'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({'status': 'Published scene to company'})

    @detail_route(methods=["post"])  # denied after publish to world
    def publish_world(self, request, pk=None):
        published = self.get_object().publish_world(request.user)

        if not published:
            return Response(
                {'status': 'Something went wrong publishing scene to world'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({'status': 'Published scene to world'})

    @detail_route(methods=["get"])
    def export(self, request, pk=None):
        scene = self.get_object()

        options = self.request.query_params.getlist('options', [])
        # What we will export, now ; separated (doesn't work), should be list
        # as in https://delft3dgt-local:8000/api/v1/scenes/44/
        # export/?options=export_images&options=export_input

        if len(options) > 0:
            stream, filename = scene.export(options)

            resp = HttpResponse(
                stream.getvalue(),
                content_type="application/x-zip-compressed"
            )
            resp[
                'Content-Disposition'] = 'attachment; filename={}'.format(
                    filename
            )

            return resp
        else:
            return Response({'status': 'No export options given'},
                            status=status.HTTP_400_BAD_REQUEST)


class SearchFormViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows search forms to be viewed.
    """

    serializer_class = SearchFormSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return SearchForm.objects.filter(name="MAIN")


class TemplateViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows templates to be viewed or edited.
    """

    serializer_class = TemplateSerializer
    permission_classes = (permissions.IsAuthenticated,
                          ViewObjectPermissions,)
    # filter_backends = (filters.DjangoObjectPermissionsFilter,)

    def get_queryset(self):
        return Template.objects.all()


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows templates to be viewed or edited.
    """

    serializer_class = UserSerializer

    queryset = User.objects.all()
    # filter_backends = (filters.DjangoObjectPermissionsFilter,)

    @list_route()
    def me(self, request):

        me = User.objects.filter(pk=request.user.pk)

        serializer = self.get_serializer(me, many=True)

        return Response(serializer.data)


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """

    serializer_class = GroupSerializer
    # filter_backends = (filters.DjangoObjectPermissionsFilter,)
    queryset = Group.objects.none()  # Required for DjangoModelPermissions

    def get_queryset(self):
        user = get_object_or_404(User, id=self.request.user.id)
        wanted = [group.id for group in user.groups.all()]
        return Group.objects.filter(pk__in=wanted)
