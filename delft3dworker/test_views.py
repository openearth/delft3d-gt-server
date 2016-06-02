from django.contrib.auth.models import User
from django.test import TestCase

from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.views import ScenarioViewSet
from delft3dworker.views import SceneViewSet


class ListAccessTestCase(TestCase):

    def setUp(self):

        # set up request factory
        self.factory = APIRequestFactory()

        # create users and store for later access
        self.user_foo = User.objects.create(username='foo')
        self.user_bar = User.objects.create(username='bar')

        # create models in dB
        scenario = Scenario.objects.create(
            name='Test Scenario',
            owner=self.user_foo,
        )
        Scene.objects.create(
            name='Test Scene 1',
            owner=self.user_foo,
            parameters={'a': {'values': 2}},
            scenario=scenario,
            state='SUCCESS',
        )
        Scene.objects.create(
            name='Test Scene 2',
            owner=self.user_foo,
            parameters={'a': {'values': 3}},
            scenario=scenario,
            state='SUCCESS',
        )

    def test_search(self):
        """
        Tests GET access rights on list Views
        """

        # User Foo can access all models
        self.assertEqual(
            len(self._request(ScenarioViewSet, self.user_foo)),
            1
        )
        self.assertEqual(
            len(self._request(SceneViewSet, self.user_foo)),
            2
        )

        # User Foo can access no models
        self.assertEqual(
            len(self._request(ScenarioViewSet, self.user_bar)),
            0
        )
        self.assertEqual(
            len(self._request(SceneViewSet, self.user_bar)),
            0
        )

    def _request(self, viewset, user):

        # create view and request
        view = viewset.as_view({'get': 'list'})
        request = self.factory.get('/scenes/')
        force_authenticate(request, user=user)

        # send request to view and render response
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 200)

        return response.data


class SceneSearchTestCase(TestCase):

    def setUp(self):
        self.user_bar = User.objects.create(username='bar')
        scenario = Scenario.objects.create(
            name='Test',
            owner=self.user_bar,
        )
        Scene.objects.create(
            name='Test',
            owner=self.user_bar,
            parameters={'a': {'values': 2}},
            scenario=scenario,
            state='SUCCESS',
        )

    def test_search(self):
        """
        Test search options
        """

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
        search_query_partial_c = {
            'search': "SUCC", 'search': "Te", 'search': "T"
        }

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
        force_authenticate(request, user=self.user_bar)
        response = view(request)
        response.render()
        return response.data


class SceneTestCase(TestCase):
    """
    Test custom written function SceneViewSet
    """

    def setUp(self):
        self.user_foo = User.objects.create(username="foo")
        Scene.objects.create(
            name="Test main workflow",
            owner=self.user_foo,
        )

    def test_scene_accepts_start(self):
        # call /scene/{pk}/start and test if 200 response is returned
        factory = APIRequestFactory()
        view = SceneViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/scenes/1/start')
        force_authenticate(request, user=self.user_foo)
        response = view(request, pk='1')
        response.render()
        self.assertEqual(response.status_code, 200)
