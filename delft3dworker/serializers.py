from rest_framework import serializers

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import Template


class ScenarioSerializer(serializers.HyperlinkedModelSerializer):
    """
    A default REST Framework HyperlinkedModelSerializer for the Scenario model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    class Meta:
        model = Scenario
        fields = (
            'id',
            'name',
            'template_url',
            'parameters',
            'scene_set',
        )


class SceneSerializer(serializers.HyperlinkedModelSerializer):
    """
    A default REST Framework HyperlinkedModelSerializer for the Scene model
    source: http://www.django-rest-framework.org/api-guide/serializers/
    """

    # here we will write custom serialization and validation methods

    class Meta:
        model = Scene
        fields = (
            'id',
            'name',
            'suid',
            'scenario_url',
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
