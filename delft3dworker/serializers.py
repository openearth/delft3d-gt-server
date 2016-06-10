from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import Template

from django.contrib.auth.models import Group
from django.contrib.auth.models import User


class UserSerializer(serializers.HyperlinkedModelSerializer):
    """
    A default REST Framework HyperlinkedModelSerializer for the User model
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


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    """
    A default REST Framework HyperlinkedModelSerializer for the Group model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
        )


class ScenarioSerializer(serializers.ModelSerializer):
    """
    A default REST Framework HyperlinkedModelSerializer for the Scenario model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    owner_url = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='user-detail',
        source='owner'
    )

    class Meta:
        model = Scenario
        fields = (
            'id',
            'name',
            'owner_url',
            'template',
            'parameters',
            'scene_set',
        )


class SceneSerializer(serializers.ModelSerializer):
    """
    A default REST Framework HyperlinkedModelSerializer for the Scene model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    owner = UserSerializer(read_only=True)

    # Run update state on serialization
    state = serializers.CharField(source='_update_state')

    class Meta:
        model = Scene
        fields = (
            'id',
            'name',
            'owner',
            'shared',
            'suid',
            'scenario',
            'fileurl',
            'info',
            'parameters',
            'state',
            'task_id',
            'workingdir',
        )


class TemplateSerializer(serializers.HyperlinkedModelSerializer):
    """
    A default REST Framework HyperlinkedModelSerializer for the Template model
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
