from django.test import TestCase
from rest_framework.test import APIRequestFactory

from delft3dworker.models import Scene
from delft3dworker.views import SceneViewSet



class SceneTestCase(TestCase):

    """
    test custom written function SceneViewSet
    """

    def setUp(self):
        # create record in database
        Scene.objects.create(name="Test main workflow", id=1)

    def test_scene_parses_input(self):
        # call /scene/{pk}/start and test if 200 response is returned
        factory = APIRequestFactory()
        view = SceneViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/scenes/1/start')
        response = view(request, pk='1')
        response.render()
        self.assertEqual(response.status_code, 200)
