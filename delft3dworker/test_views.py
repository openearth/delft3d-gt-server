from django.test import TestCase

from delft3dworker.models import Scene, Scenario
from delft3dworker.views import SceneViewSet
from rest_framework.test import APIRequestFactory

class SceneTestCase(TestCase):
    def setUp(self):
        Scene.objects.create(name="Test main workflow", id=1)

    def test_scene_parses_input(self):
        factory = APIRequestFactory()
        view = SceneViewSet.as_view({'get':'retrieve'})
        request = factory.get('/scenes/1/start/', {'pk': 1}, format='json')
        response = view(request)

