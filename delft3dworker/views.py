"""
Views for the ui.
"""
from __future__ import absolute_import

import io
import logging
import zipfile
from datetime import timedelta

import django_filters
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from django_filters import rest_framework as e_filters
from guardian.shortcuts import assign_perm, get_objects_for_user
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_guardian import filters as guardian_filter

from delft3dworker.models import Scenario, Scene, SearchForm, Template, Version_Docker
from delft3dworker.permissions import ExtendedScenePermission, ViewObjectPermissions
from delft3dworker.serializers import (
    GroupSerializer,
    ScenarioSerializer,
    SceneFullSerializer,
    SceneSparseSerializer,
    SearchFormSerializer,
    TemplateSerializer,
    UserSerializer,
    VersionSerializer,
)
from delft3dworker.utils import tz_midnight

# ################################### REST


# ### Filters


class ScenarioFilter(e_filters.FilterSet):
    """
    FilterSet to filter Scenarios on complex queries
    Needs an exact match (!)
    """

    class Meta:
        model = Scenario
        fields = [
            "name",
        ]


class SceneFilter(e_filters.FilterSet):
    """
    FilterSet to filter Scenes on complex queries, such as
    template, traversing db relationships.
    Needs an exact match (!)
    """

    scenario = django_filters.CharFilter(field_name="scenario__name")

    class Meta:
        model = Scene
        fields = ["name", "state", "scenario"]


# ### ViewSets


class ScenarioViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows scenarios to be viewed or edited.
    """

    serializer_class = ScenarioSerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        guardian_filter.ObjectPermissionsFilter,
    )
    permission_classes = (
        permissions.IsAuthenticated,
        ViewObjectPermissions,
    )

    # Default ordering by id, so latest run is last in list
    # reverse by setting ('-id',)
    ordering = ("id",)

    # Our own custom filter to create custom search fields
    # this creates &name= among others
    filterset_class = ScenarioFilter

    queryset = Scenario.objects.none()

    def get_queryset(self):
        queryset = Scenario.objects.all()
        return queryset.order_by("name")

    def perform_create(self, serializer):
        if serializer.is_valid():
            instance = serializer.save()
            instance.owner = self.request.user

            parameters = (
                serializer.validated_data["parameters"]
                if ("parameters" in serializer.validated_data)
                else None
            )

            if parameters:
                # we're adding the template to the parameters
                parameters["template"] = {"values": [instance.template.name]}
                instance.load_settings(parameters)
                instance.createscenes(self.request.user)

            assign_perm("add_scenario", self.request.user, instance)
            assign_perm("change_scenario", self.request.user, instance)
            assign_perm("delete_scenario", self.request.user, instance)
            assign_perm("view_scenario", self.request.user, instance)

            instance.save()

    # Pass on user to check permissions
    def perform_destroy(self, instance):
        instance.delete(self.request.user)

    @action(methods=["put"], detail=True)  # denied after publish to company/world
    def start(self, request, pk=None):
        scenario = self.get_object()
        scenario.start(request.user)
        serializer = self.get_serializer(scenario)

        return Response(serializer.data)

    @action(methods=["put"], detail=True)  # denied after publish to company/world
    def stop(self, request, pk=None):
        scenario = self.get_object()

        scenario.abort()

        serializer = self.get_serializer(scenario)

        return Response(serializer.data)

    @action(methods=["post"], detail=True)  # denied after publish to world
    def publish_company(self, request, pk=None):
        self.get_object().publish_company(request.user)
        return Response({"status": "Published scenario to company"})

    @action(methods=["post"], detail=True)  # denied after publish to world
    def publish_world(self, request, pk=None):
        self.get_object().publish_world(request.user)
        return Response({"status": "Published scenario to world"})


class SceneViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows scenes to be viewed or edited.
    """

    serializer_class = SceneSparseSerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        guardian_filter.DjangoObjectPermissionsFilter,
    )
    # Default order by name, so runs don't jump around
    ordering = ("id",)

    # Our own custom filter to create custom search fields
    # this creates &template= among others
    filterset_class = SceneFilter

    # Searchfilter backend for field &search=
    search_fields = ("name",)

    # Permissions backend which we could use in filter
    permission_classes = (
        permissions.IsAuthenticated,
        ViewObjectPermissions,
    )

    # If we overwrite get queryset
    queryset = Scene.objects.none()

    def get_serializer_class(self):
        """Override serializer for lite list."""
        if self.action == "list":
            return SceneSparseSerializer
        else:
            return SceneFullSerializer

    def perform_create(self, serializer):
        if serializer.is_valid():
            instance = serializer.save()
            instance.owner = self.request.user
            instance.shared = "p"  # private
            instance.save()

            assign_perm("view_scene", self.request.user, instance)
            assign_perm("add_scene", self.request.user, instance)
            assign_perm("change_scene", self.request.user, instance)
            assign_perm("delete_scene", self.request.user, instance)

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

        # Filter on parameter
        parameters = self.request.query_params.getlist("parameter", [])
        template = self.request.query_params.getlist("template", [])
        shared = self.request.query_params.getlist("shared", [])
        users = self.request.query_params.getlist("users", [])

        outdated = self.request.query_params.get("outdated", "")
        created_after = self.request.query_params.get("created_after", "")
        created_before = self.request.query_params.get("created_before", "")
        started_after = self.request.query_params.get("started_after", "")
        started_before = self.request.query_params.get("started_before", "")

        # explained later
        temp_workaround = False

        if len(parameters) > 0:
            # Processing user input
            # will sometimes fail
            try:
                for parameter in parameters:

                    p = parameter.split(",")
                    p = [val for val in p if val != ""]

                    # Key, min, max lookup
                    if len(p) == 3:

                        key, minvalue, maxvalue = p
                        logging.info(
                            "Lookup value [{} - {}] for parameter {}".format(
                                minvalue, maxvalue, key
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

                                # filter on input parameters
                                value = scene.parameters.get(key, {}).get(
                                    "value", "None"
                                )
                                if (value != "None") and (
                                    minvalue <= value <= maxvalue
                                ):
                                    wanted.append(scene.id)

                                # filter on postprocessing output
                                postprocess_output = scene.info.get(
                                    "postprocess_output"
                                )

                                if key in postprocess_output:
                                    value = postprocess_output[key]
                                    if minvalue <= value <= maxvalue:
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

                            logging.info("Lookup value for parameter {}".format(key))

                            for scene in queryset:
                                if (
                                    scene.parameters.get(key, {}).get("value", "")
                                    == value
                                ):
                                    wanted.append(scene.id)

                        queryset = queryset.filter(pk__in=wanted)

            except Exception as e:
                logging.exception(
                    "Search with params {} and template {} failed".format(
                        parameters, template
                    )
                )
                return Scene.objects.none()

        if len(template) > 0:
            queryset = queryset.filter(scenario__template__name__in=template).distinct()

        if len(shared) > 0:
            lookup = {"private": "p", "company": "c", "public": "w"}
            wanted = [lookup[share] for share in shared if share in lookup]
            queryset = queryset.filter(shared__in=wanted)

        if len(users) > 0:
            userids = [int(user) for user in users if user.isdigit()]
            queryset = queryset.filter(owner__in=userids)

        if outdated != "":
            pass

        if created_after != "":
            created_after_date = parse_date(created_after)
            if created_after_date:
                dt = tz_midnight(created_after_date)
                queryset = queryset.filter(date_created__gte=dt)

        if created_before != "":
            created_before_date = parse_date(created_before)
            if created_before_date:
                dt = tz_midnight(created_before_date + timedelta(days=1))
                queryset = queryset.filter(date_created__lte=dt)

        if started_after != "":
            started_after_date = parse_date(started_after)
            if started_after_date:
                dt = tz_midnight(started_after_date)
                queryset = queryset.filter(date_started__gte=dt)

        if started_before != "":
            started_before_date = parse_date(started_before)
            if started_before_date:
                dt = tz_midnight(started_before_date + timedelta(days=1))
                queryset = queryset.filter(date_started__lte=dt)

        return queryset.distinct().order_by("name")

    @action(detail=True, methods=["put"])  # denied after publish to company/world
    def reset(self, request, pk=None):
        scene = self.get_object()
        scene.reset()
        serializer = self.get_serializer(scene)

        return Response(serializer.data)

    @action(methods=["put"], detail=True)  # denied after publish to company/world
    def start(self, request, pk=None):
        scene = self.get_object()
        scene.start()
        serializer = self.get_serializer(scene)

        return Response(serializer.data)

    @action(
        methods=["put"],
        detail=True,
        permission_classes=[permissions.IsAuthenticated, ExtendedScenePermission],
    )
    def redo(self, request, pk=None):
        # Update and redo the mode, based on a specific entrypoint
        d = request.data
        valid = False  # True if redo passes successfully

        # Check if we got a dictionary
        # with a valid entrypoint
        if isinstance(d, dict):
            entrypoint = d.get("entrypoint", None)
            if entrypoint is not None:
                scene = self.get_object()
                valid = scene.redo(entrypoint)

        if valid:
            serializer = self.get_serializer(scene)
            return Response(serializer.data)
        else:
            return Response(
                "No (valid) entrypoint provided.", status=status.HTTP_400_BAD_REQUEST
            )

    @action(methods=["put"], detail=True)  # denied after publish to company/world
    def stop(self, request, pk=None):
        scene = self.get_object()
        scene.abort()
        serializer = self.get_serializer(scene)

        return Response(serializer.data)

    @action(methods=["post"], detail=True)  # denied after publish to world
    def publish_company(self, request, pk=None):
        published = self.get_object().publish_company(request.user)

        if not published:
            return Response(
                {"status": "Something went wrong publishing scene to company"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"status": "Published scene to company"})

    @action(methods=["post"], detail=False)  # denied after publish to world
    def publish_company_all(self, request):

        try:
            queryset = Scene.objects.filter(owner=self.request.user).filter(
                suid__in=request.data.getlist("suid", [])
            )
            for scene in queryset:
                scene.publish_company(request.user)
        except (ValidationError, ValueError) as e:
            return Response({"status": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"status": "Published scenes to company"})

    @action(methods=["post"], detail=True)  # denied after publish to world
    def publish_world(self, request, pk=None):
        published = self.get_object().publish_world(request.user)

        if not published:
            return Response(
                {"status": "Something went wrong publishing scene to world"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"status": "Published scene to world"})

    @action(methods=["post"], detail=False)  # denied after publish to world
    def publish_world_all(self, request):

        try:
            queryset = Scene.objects.filter(owner=self.request.user).filter(
                suid__in=request.data.getlist("suid", [])
            )
            for scene in queryset:
                scene.publish_world(request.user)
        except (ValidationError, ValueError) as e:
            return Response({"status": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"status": "Published scenes to world"})

    @action(
        methods=["get"],
        detail=True,
        permission_classes=[permissions.IsAuthenticated, ExtendedScenePermission],
    )
    def export(self, request, pk=None):
        # Alternatives to this implementation are:
        # - django-zip-view (sets mimetype and content-disposition)
        # - django-filebrowser (filtering and more elegant browsing)

        # from:
        # http://stackoverflow.com/questions/67454/serving-dynamically-generated-zip-archives-in-django

        options = self.request.query_params.getlist("options", [])
        if len(options) == 0:
            return Response(
                {"status": "No export options given"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scene = self.get_object()

        # The zip compressor
        # Open BytesIO to grab in-memory ZIP contents
        # (be explicit about bytes)
        stream = io.BytesIO()
        zf = zipfile.ZipFile(stream, "w", zipfile.ZIP_STORED, True)
        files_added = scene.export(zf, options)
        zf.close()

        if not files_added:
            return Response(
                {"status": "Empty zip file: selected files do not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resp = HttpResponse(
            stream.getvalue(), content_type="application/x-zip-compressed"
        )
        resp["Content-Disposition"] = "attachment; filename={}".format(
            "{}.zip".format(slugify(scene.name))
        )

        return resp

    @action(
        methods=["get"],
        detail=False,
        permission_classes=[permissions.IsAuthenticated, ExtendedScenePermission],
    )
    def export_all(self, request):
        # Alternatives to this implementation are:
        # - django-zip-view (sets mimetype and content-disposition)
        # - django-filebrowser (filtering and more elegant browsing)

        # from:
        # http://stackoverflow.com/questions/67454/serving-dynamically-generated-zip-archives-in-django

        options = self.request.query_params.getlist("options", [])
        if len(options) == 0:
            return Response(
                {"status": "No export options given"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = get_objects_for_user(
            self.request.user,
            "delft3dworker.extended_view_scene",
            accept_global_perms=False,
        ).filter(suid__in=request.query_params.getlist("suid", []))
        if len(queryset) == 0:
            return Response(
                {
                    "status": "Either no scenes were requested or you don't have permission to view any."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # The zip compressor
        # Open BytesIO to grab in-memory ZIP contents
        # (be explicit about bytes)
        stream = io.BytesIO()
        zf = zipfile.ZipFile(stream, "w", zipfile.ZIP_STORED, True)
        files_added = False
        for scene in queryset:
            files_added = scene.export(zf, options) or files_added
        zf.close()

        if not files_added:
            return Response(
                {"status": "Empty zip file: selected files do not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resp = HttpResponse(
            stream.getvalue(), content_type="application/x-zip-compressed"
        )
        resp["Content-Disposition"] = "attachment; filename=Delft3DGTFiles.zip"
        return resp

    @action(methods=["get"], detail=False)
    def versions(self, request):
        return Response({})


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
    permission_classes = (
        permissions.IsAuthenticated,
        ViewObjectPermissions,
    )

    def get_queryset(self):
        return Template.objects.all()


class VersionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows templates to be viewed or edited.
    """

    serializer_class = VersionSerializer
    permission_classes = (
        permissions.IsAuthenticated,
        ViewObjectPermissions,
    )

    def get_queryset(self):
        return Version_Docker.objects.all()


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows templates to be viewed or edited.
    """

    serializer_class = UserSerializer
    queryset = User.objects.all()

    def get_queryset(self):
        user = get_object_or_404(User, id=self.request.user.id)
        wanted = [
            group.name
            for group in user.groups.exclude(name="access:world").exclude(
                name="access:world_restricted"
            )
        ]
        queryset = User.objects.filter(groups__name__in=wanted)
        return queryset

    @action(detail=False)
    def me(self, request):

        me = User.objects.filter(pk=request.user.pk)

        serializer = self.get_serializer(me, many=True)

        return Response(serializer.data)


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """

    serializer_class = GroupSerializer
    queryset = Group.objects.none()  # Required for DjangoModelPermissions

    def get_queryset(self):
        user = get_object_or_404(User, id=self.request.user.id)
        wanted = [group.id for group in user.groups.all()]
        return Group.objects.filter(pk__in=wanted)


class GroupUsageSummaryViewSet(viewsets.ModelViewSet):
    """
    View of Docker container usage summary, sorted by group.
    """

    serializer_class = GroupSerializer
    queryset = Group.objects.none()  # Required for DjangoModelPermissions


class UserUsageSummaryViewSet(viewsets.ModelViewSet):
    """
    View of Docker container usage summary for a group, sorted by user.
    """

    serializer_class = UserSerializer
    queryset = User.objects.none()  # Required for DjangoModelPermissions
