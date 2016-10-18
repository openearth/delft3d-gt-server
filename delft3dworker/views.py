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


# ### Filters

class ScenarioFilter(filters.FilterSet):
    """
    FilterSet to filter Scenarios on complex queries
    Needs an exact match (!)
    """
    class Meta:
        model = Scenario
        fields = ['name', ]


class SceneFilter(filters.FilterSet):
    """
    FilterSet to filter Scenes on complex queries, such as
    template, traversing db relationships.
    Needs an exact match (!)
    """
    scenario = django_filters.CharFilter(name="scenario__name")

    class Meta:
        model = Scene
        fields = ['name', 'state', 'scenario']


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
    filter_class = ScenarioFilter

    queryset = Scenario.objects.none()

    def get_queryset(self):
        queryset = Scenario.objects.all()

        return queryset.order_by('name')

    def perform_create(self, serializer):
        if serializer.is_valid():
            instance = serializer.save()
            instance.owner = self.request.user

            # Inspect validated field data.
            parameters = serializer.validated_data['parameters'] if (
                'parameters' in serializer.validated_data
            ) else None

            if parameters:
                # we're adding the template to the parameters
                parameters['template'] = {'values': [instance.template.name]}
                instance.load_settings(parameters)
                instance.createscenes(self.request.user)

            assign_perm('add_scenario', self.request.user, instance)
            assign_perm('change_scenario', self.request.user, instance)
            assign_perm('delete_scenario', self.request.user, instance)
            assign_perm('view_scenario', self.request.user, instance)

            instance.save()

    # Pass on user to check permissions
    def perform_destroy(self, instance):
        instance.delete(self.request.user)

    @detail_route(methods=["put"])  # denied after publish to company/world
    def start(self, request, pk=None):
        scenario = self.get_object()
        scenario.start(request.user)
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

    # Our own custom filter to create custom search fields
    # this creates &template= among others
    filter_class = SceneFilter

    # Searchfilter backend for field &search=
    # Filters on fields below beginning with value (^)
    search_fields = ('$name',)

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

            TODO: This method needs to be rewritten, badly
        """
        queryset = Scene.objects.all()
        # self.queryset = queryset

        # Filter on parameter
        parameters = self.request.query_params.getlist('parameter', [])
        template = self.request.query_params.getlist('template', [])
        shared = self.request.query_params.getlist('shared', [])
        users = self.request.query_params.getlist('users', [])

        # explained later
        temp_workaround = False

        if len(parameters) > 0:
            # Processing user input
            # will sometimes fail
            try:
                for parameter in parameters:

                    p = parameter.split(',')
                    p = [val for val in p if val != '']

                    # Key, min, max lookup
                    if len(p) == 3:

                        key, minvalue, maxvalue = p
                        logging.info(
                            "Lookup value [{} - {}] for parameter {}".format(
                                minvalue,
                                maxvalue,
                                key
                            )
                        )

                        try:
                            # Find integers or floats
                            minvalue = float(minvalue)
                            maxvalue = float(maxvalue)

                            # Create json lookup
                            # q = {key: {'value': value}}

                            # Not yet possible to do json queries directly
                            # Requires JSONField from Postgresql 9.4 and Django
                            # 1.9 So we loop manually (bad performance!)
                            wanted = []
                            for scene in queryset:
                                value = scene.parameters.get(
                                    key, {}).get('value', 'None')
                                if (minvalue <= value <= maxvalue) or (
                                        value == 'None'):
                                    wanted.append(scene.id)

                            queryset = queryset.filter(pk__in=wanted)
                        except ValueError:
                            pass  # no floats? no results
                            temp_workaround = True

                    # The front-end is supposed to provide sediment
                    # compositions as follows:
                    #
                    # ...?parameter=composition,sand-clay&parameter=composition,mud
                    #
                    # however, now it provides it as follows:
                    #
                    # ...?parameter=composition,sand-clay,mud
                    #
                    # hence this temp_workaround:
                    if temp_workaround or len(p) == 2 or len(p) > 3:
                        key = p[0]
                        values = p[1:]
                        wanted = []

                        queryset = queryset.filter(parameters__icontains=key)

                        for value in values:

                            # a blatant copy-paste of the above, because I
                            # cannot be bothered

                            logging.info(
                                "Lookup value for parameter {}".format(key))

                            for scene in queryset:
                                if scene.parameters.get(
                                        key, {}).get('value', '') == value:
                                    wanted.append(scene.id)

                        queryset = queryset.filter(pk__in=wanted)

            except Exception as e:
                logging.exception(
                    "Search with params {} and template {} failed".format(
                        parameters, template)
                )
                return Scene.objects.none()

        if len(template) > 0:
            queryset = queryset.filter(
                scenario__template__name__in=template).distinct()

        if len(shared) > 0:
            lookup = {"private": "p", "company": "c", "public": "w"}
            wanted = [lookup[share] for share in shared if share in lookup]
            queryset = queryset.filter(shared__in=wanted)

        if len(users) > 0:
            userids = [int(user) for user in users if user.isdigit()]
            queryset = queryset.filter(owner__in=userids)

        # self.queryset = queryset

        return queryset.order_by('name')

    @detail_route(methods=["put"])  # denied after publish to company/world
    def start(self, request, pk=None):

        scene = self.get_object()
        scene.start()
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
