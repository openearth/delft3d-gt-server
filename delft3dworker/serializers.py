from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import SearchForm
from delft3dworker.models import Template

from django.contrib.auth.models import Group
from django.contrib.auth.models import User


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


class SceneSerializer(serializers.ModelSerializer):
    """
    A default REST Framework ModelSerializer for the Scene model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    owner = UserSerializer(read_only=True)

    state = serializers.CharField(source='get_phase_display', read_only=True)

    class Meta:
        model = Scene
        fields = (
            'id',
            'name',
            'state',
            'progress',
            'owner',
            'shared',
            'suid',
            'scenario',
            'fileurl',
            'info',
            'parameters',
            'task_id',
            'workingdir',
            'phase'
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
