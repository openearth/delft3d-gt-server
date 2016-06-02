from django.test import TestCase

from delft3dworker.models import Scene, Scenario
from delft3dworker.views import SceneViewSet
from rest_framework.test import APIRequestFactory

class SceneSearchTestCase(TestCase):
    def setUp(self):
        scenario = Scenario.objects.create(name='Test')
        Scene.objects.create(name="Test",
            scenario=scenario,
            state="SUCCESS",
            parameters={'a': {'values': 2}}
            )

    def test_search(self):
        """Test search options."""

        # Exact matches
        search_query_exact_a = {'name': "Test"}
        search_query_exact_b = {'name': "Test2"}
        search_query_exact_c = {'scenario': "Test", 'name': "Test"}

        self.assertEqual(len(self._request(search_query_exact_a)), 1)
        self.assertEqual(len(self._request(search_query_exact_b)), 0)
        self.assertEqual(len(self._request(search_query_exact_c)), 1)

        # Partial matches from beginning of line
        search_query_partial_a = {'search': "Te"}
        search_query_partial_b = {'search': "Tes"}
        search_query_partial_c = {'search': "SUCC", 'search': "Te", 'search': "T"}

        self.assertEqual(len(self._request(search_query_partial_a)), 1)
        self.assertEqual(len(self._request(search_query_partial_b)), 1)
        self.assertEqual(len(self._request(search_query_partial_c)), 1)

        # Parameter searches
        search_query_parameter_a = {'parameter': "a"}
        search_query_parameter_b = {'parameter': "b"}
        search_query_parameter_c = {'parameter': "a,2"}
        search_query_parameter_d = {'parameter': "a,1"}
        search_query_parameter_e = {'parameter': "a,1,2"}
        search_query_parameter_f = {'parameter': "a,2,3"}

        self.assertEqual(len(self._request(search_query_parameter_a)), 1)
        self.assertEqual(len(self._request(search_query_parameter_b)), 0)
        self.assertEqual(len(self._request(search_query_parameter_c)), 1)
        self.assertEqual(len(self._request(search_query_parameter_d)), 0)
        self.assertEqual(len(self._request(search_query_parameter_e)), 0)
        self.assertEqual(len(self._request(search_query_parameter_f)), 1)

    def _request(self, query):
        factory = APIRequestFactory()
        view = SceneViewSet.as_view({'get': 'list'})
        request = factory.get('/scenes/', query)
        response = view(request)
        return response.data


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
