from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

from delft3dworker.models import Version_Docker
from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import SearchForm
from delft3dworker.models import Template

from django.contrib.auth.models import Group
from django.contrib.auth.models import User


class VersionSerializer(serializers.ModelSerializer):
    """
    A default REST Framework ModelSerializer for the User model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    class Meta:
        model = Version_Docker
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    """
    A default REST Framework ModelSerializer for the User model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'groups',
        )


class GroupSerializer(serializers.ModelSerializer):
    """
    A default REST Framework ModelSerializer for the Group model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
        )


class SceneFullSerializer(serializers.ModelSerializer):
    """
    A default REST Framework ModelSerializer for the Scene model, which
    is used for detail views of scenes, providing all valuable data of
    a single model to the frontend.
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    owner = UserSerializer(read_only=True)
    state = serializers.CharField(source='get_phase_display', read_only=True)
    template = serializers.SerializerMethodField()

    class Meta:
        model = Scene
        fields = (
            'date_created',
            'date_started',
            'fileurl',
            'id',
            'info',
            'name',
            'owner',
            'parameters',
            'phase',
            'progress',
            'scenario',
            'shared',
            'state',
            'suid',
            'task_id',
            'workingdir',
            'template'
        )

    def get_template(self, obj):
        scenario = obj.scenario.first()
        # Only retrieve template in case of a connected scenario
        if scenario is not None and scenario.template is not None:
            return scenario.template.name
        else:
            return None


class SceneSparseSerializer(serializers.ModelSerializer):
    """
    A default REST Framework ModelSerializer for the Scene model, which
    is used for list views of scenes, providing only essential data in
    a list of many models to the frontend.
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    state = serializers.CharField(source='get_phase_display', read_only=True)

    class Meta:
        model = Scene
        fields = (
            'suid',
            'id',
            'name',
            'owner',
            'progress',
            'shared',
            'state'
        )


class ScenarioSerializer(serializers.ModelSerializer):
    """
    A default REST Framework ModelSerializer for the Scenario model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods
    state = serializers.CharField(
        source='_update_state_and_save', read_only=True)

    owner_url = serializers.HyperlinkedRelatedField(
        read_only=True, view_name='user-detail', source='owner')

    class Meta:
        model = Scenario
        fields = (
            'id',
            'name',
            'owner_url',
            'template',
            'parameters',
            'state',
            'progress',
            'scene_set',
        )


class SearchFormSerializer(serializers.ModelSerializer):
    """
    A default REST Framework ModelSerializer for the Template model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    class Meta:
        model = SearchForm
        fields = (
            'id',
            'name',
            'sections',
            'templates',
        )


class TemplateSerializer(serializers.ModelSerializer):
    """
    A default REST Framework ModelSerializer for the Template model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    class Meta:
        model = Template
        fields = (
            'id',
            'name',
            'meta',
            'sections',
        )
