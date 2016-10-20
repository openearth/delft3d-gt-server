from __future__ import absolute_import

from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

from guardian.shortcuts import assign_perm

from mock import MagicMock
from mock import patch

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import Template
from delft3dworker.views import ScenarioViewSet
from delft3dworker.views import SceneViewSet
from delft3dworker.views import UserViewSet


class ApiAccessTestCase(TestCase):
    """
    ApiAccessTestCase
    Tests the Django REST API in combination Django Guardian:
    Do we protect our models correctly?
    """

    def setUp(self):

        # set up request factory
        self.factory = APIRequestFactory()

        # create users and store for later access
        self.user_foo = User.objects.create_user(
            username='foo', password="secret")
        self.user_bar = User.objects.create_user(
            username='bar', password="secret")

        # create models in dB
        self.template = Template.objects.create(
            name='Test Template',
        )
        self.scenario = Scenario.objects.create(
            name='Test Scenario',
            owner=self.user_foo,
            template=self.template
        )
        a = Scene.objects.create(
            name='Test Scene 1',
            owner=self.user_foo,
            parameters={
                'a': {'values': 2},
            },
            state='SUCCESS',
            shared='p',
        )
        a.scenario.add(self.scenario)
        b = Scene.objects.create(
            name='Test Scene 2',
            owner=self.user_foo,
            parameters={
                'a': {'values': 3},
            },
            state='SUCCESS',
            shared='p',
        )
        b.scenario.add(self.scenario)

        # Model general
        self.user_foo.user_permissions.add(
            Permission.objects.get(codename='view_scenario'))
        self.user_foo.user_permissions.add(
            Permission.objects.get(codename='add_scenario'))
        self.user_foo.user_permissions.add(
            Permission.objects.get(codename='delete_scenario'))
        self.user_foo.user_permissions.add(
            Permission.objects.get(codename='view_scene'))
        self.user_bar.user_permissions.add(
            Permission.objects.get(codename='view_scenario'))
        self.user_bar.user_permissions.add(
            Permission.objects.get(codename='view_scene'))

        # Object general
        assign_perm('view_scenario', self.user_foo, self.scenario)
        assign_perm('change_scenario', self.user_foo, self.scenario)
        assign_perm('delete_scenario', self.user_foo, self.scenario)

        assign_perm('view_scene', self.user_foo, a)
        assign_perm('change_scene', self.user_foo, a)
        assign_perm('delete_scene', self.user_foo, a)
        assign_perm('view_scene', self.user_foo, b)
        assign_perm('change_scene', self.user_foo, b)
        assign_perm('delete_scene', self.user_foo, b)

        # Refetch to empty permissions cache
        self.user_foo = User.objects.get(pk=self.user_foo.pk)
        self.user_bar = User.objects.get(pk=self.user_bar.pk)

    @patch('delft3dworker.models.Scenario.start', autospec=True,)
    def test_scenario_post(self, mockedStartMethod):
        # list view for POST (create new)
        url = reverse('scenario-list')

        self.client.login(username='foo', password='secret')
        data = {
            "name": "New Scenario",
            "parameter": "/data/1be8dcc1-cf00-418c-9920-efa07b4fbeca/",
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mockedStartMethod.call_count, 0)

    def test_search(self):
        # User Foo can access own models

        self.assertEqual(
            len(self._request(ScenarioViewSet, self.user_foo)), 1)

        self.assertEqual(
            len(self._request(SceneViewSet, self.user_foo)), 2)

        # User Bar can access only two own models (because Bar owns none)
        self.assertEqual(
            len(self._request(ScenarioViewSet, self.user_bar)), 0)
        self.assertEqual(
            len(self._request(SceneViewSet, self.user_bar)), 0)

    def _request(self, viewset, user):
        # create view and request
        view = viewset.as_view({'get': 'list'})
        request = self.factory.get('/scenes/')
        force_authenticate(request, user=user)

        # send request to view and render response
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        return response.data


class SceneTestCase(APITestCase):
    """
    SceneTestCase
    Tests the Scene Django REST API
    """

    def setUp(self):
        # create Users and assign permissions
        self.user_foo = User.objects.create_user(
            username="foo",
            password="secret"
        )
        self.user_bar = User.objects.create_user(
            username="bar",
            password="secret"
        )
        for user in [self.user_foo, self.user_bar]:
            for perm in ['view_scene', 'add_scene',
                         'change_scene', 'delete_scene']:
                user.user_permissions.add(
                    Permission.objects.get(codename=perm))

        # create Scene instance and assign permissions for user_foo
        self.scene_1 = Scene.objects.create(
            name="Test main workflow",
            owner=self.user_foo,
            shared='p',
        )
        for perm in ['view_scene', 'add_scene',
                     'change_scene', 'delete_scene']:
            assign_perm(perm, self.user_foo, self.scene_1)

    def test_scene_get(self):
        # detail view
        url = reverse('scene-detail', args=[self.scene_1.pk])

        # foo can see
        self.client.login(username='foo', password='secret')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # bar cannot see
        self.client.login(username='bar', password='secret')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_scene_post(self):
        # list view for POST (create new)
        url = reverse('scene-list')

        # foo can create
        self.client.login(username='foo', password='secret')
        data = {
            "name": "New Scene",
            "task_id": "78a38bbd-4041-4b34-a889-054d2dee3ea4",
            "workingdir": "/data/1be8dcc1-cf00-418c-9920-efa07b4fbeca/",
            "shared": "p",
            "fileurl": "/files/1be8dcc1-cf00-418c-9920-efa07b4fbeca/"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # bar can create
        self.client.login(username='bar', password='secret')
        data = {
            "name": "New Scene",
            "task_id": "78a38bbd-4041-4b34-a889-054d2dee3ea4",
            "workingdir": "/data/1be8dcc1-cf00-418c-9920-efa07b4fbeca/",
            "shared": "p",
            "fileurl": "/files/1be8dcc1-cf00-418c-9920-efa07b4fbeca/"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_scene_put(self):
        # detail view for PUT (udpate)
        url = reverse('scene-detail', args=[self.scene_1.pk])

        # foo can update
        self.client.login(username='foo', password='secret')
        data = {
            "name": "New Scene (updated)",
            "task_id": "78a38bbd-4041-4b34-a889-054d2dee3ea4",
            "workingdir": "/data/1be8dcc1-cf00-418c-9920-efa07b4fbeca/",
            "shared": "p",
            "fileurl": "/files/1be8dcc1-cf00-418c-9920-efa07b4fbeca/"
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # bar cannot update
        self.client.login(username='bar', password='secret')
        data = {
            "name": "New Scene (updated)",
            "task_id": "78a38bbd-4041-4b34-a889-054d2dee3ea4",
            "workingdir": "/data/1be8dcc1-cf00-418c-9920-efa07b4fbeca/",
            "shared": "p",
            "fileurl": "/files/1be8dcc1-cf00-418c-9920-efa07b4fbeca/"
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_scene_no_put_after_publish(self):
        # the scene is published
        self.scene_1.publish_company(self.user_foo)

        # detail view for PUT (update)
        url = reverse('scene-detail', args=[self.scene_1.pk])

        # foo cannot update
        self.client.login(username='foo', password='secret')
        data = {
            "name": "New Scene (updated)",
            "task_id": "78a38bbd-4041-4b34-a889-054d2dee3ea4",
            "workingdir": "/data/1be8dcc1-cf00-418c-9920-efa07b4fbeca/",
            "shared": "p",
            "fileurl": "/files/1be8dcc1-cf00-418c-9920-efa07b4fbeca/"
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # bar cannot update
        self.client.login(username='bar', password='secret')
        data = {
            "name": "New Scene (updated)",
            "task_id": "78a38bbd-4041-4b34-a889-054d2dee3ea4",
            "workingdir": "/data/1be8dcc1-cf00-418c-9920-efa07b4fbeca/",
            "shared": "p",
            "fileurl": "/files/1be8dcc1-cf00-418c-9920-efa07b4fbeca/"
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('delft3dworker.models.Scene.start', autospec=True)
    def test_scene_start(self, mocked_scene_method):
        # start view
        url = reverse('scene-start', args=[self.scene_1.pk])

        # bar cannot see
        self.client.login(username='bar', password='secret')
        response = self.client.put(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(mocked_scene_method.call_count, 0)

        # foo can start
        self.client.login(username='foo', password='secret')
        response = self.client.put(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_scene_method.assert_called_with(self.scene_1)

    @patch('delft3dworker.models.Scene.start', autospec=True)
    def test_scene_no_start_after_publish(self, mocked_scene_method):
        # the scene is published
        self.scene_1.publish_company(self.user_foo)

        # start view
        url = reverse('scene-start', args=[self.scene_1.pk])

        # foo cannot start (forbidden)
        self.client.login(username='foo', password='secret')
        response = self.client.put(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(mocked_scene_method.call_count, 0)


class SceneSearchTestCase(TestCase):
    """
    SceneSearchTestCase
    Tests the Scene search functionality using Django REST filters
    """

    def setUp(self):
        self.user_bar = User.objects.create_user(
            username='bar',
            password='secret'
        )
        self.scenario = Scenario.objects.create(
            name='Testscenario',
            owner=self.user_bar,
        )
        self.scene_1 = Scene.objects.create(
            name='Testscene 1',
            owner=self.user_bar,
            parameters={
                'a': {'value': 2},
                'hack': {'value': 'mud'},
            },
            state='SUCCESS',
            shared='p',
        )
        self.scene_1.scenario.add(self.scenario)
        self.scene_1.info = {
            'postprocess_output': {
                'postproc_x': 0.1
            }
        }
        self.scene_1.save()

        self.scene_2 = Scene.objects.create(
            name='Testscene 2',
            owner=self.user_bar,
            parameters={
                'a': {'value': 3},
                'hack': {'value': 'grease'},
            },
            state='SUCCESS',
            shared='p',
        )
        self.scene_2.scenario.add(self.scenario)
        self.scene_2.info = {
            'postprocess_output': {
                'postproc_x': 0.9,
                'postproc_y': 0.5
            }
        }
        self.scene_2.save()

        # Object general
        assign_perm('view_scenario', self.user_bar, self.scenario)
        assign_perm('view_scene', self.user_bar, self.scene_1)
        assign_perm('view_scene', self.user_bar, self.scene_2)

        # Model general
        self.user_bar.user_permissions.add(
            Permission.objects.get(codename='view_scenario'))
        self.user_bar.user_permissions.add(
            Permission.objects.get(codename='view_scene'))

        # Refetch to empty permissions cache
        self.user_bar = User.objects.get(pk=self.user_bar.pk)

    def test_search(self):
        """
        Test search options
        """

        # Exact matches
        search_query_exact_a = {'name': "Testscene 1"}
        search_query_exact_b = {'state': "FINISHED"}
        search_query_exact_c = {
            'scenario': "Testscenario", 'name': "Testscene 1"}

        self.assertEqual(len(self._request(search_query_exact_a)), 1)
        self.assertEqual(len(self._request(search_query_exact_b)), 0)
        self.assertEqual(len(self._request(search_query_exact_c)), 1)

        # Partial matches from beginning of line
        search_query_partial_a = {'search': "Te"}
        search_query_partial_b = {'search': "Tes"}
        search_query_partial_c = {
            'search': "SUCC", 'search': "Te", 'search': "T"
        }

        self.assertEqual(len(self._request(search_query_partial_a)), 2)
        self.assertEqual(len(self._request(search_query_partial_b)), 2)
        self.assertEqual(len(self._request(search_query_partial_c)), 2)

        # Parameter searches
        search_query_parameter_a = {'parameter': "a"}
        search_query_parameter_b = {'parameter': "b"}
        search_query_parameter_c = {'parameter': "a,2"}
        search_query_parameter_d = {'parameter': "a,1"}
        search_query_parameter_e = {'parameter': "a,1,2"}
        search_query_parameter_f = {'parameter': "a,2,3"}
        search_query_parameter_g = {'parameter': "a,0,1"}

        self.assertEqual(len(self._request(search_query_parameter_a)), 2)
        self.assertEqual(len(self._request(search_query_parameter_b)), 2)
        self.assertEqual(len(self._request(search_query_parameter_c)), 0)
        self.assertEqual(len(self._request(search_query_parameter_d)), 0)
        self.assertEqual(len(self._request(search_query_parameter_e)), 1)
        self.assertEqual(len(self._request(search_query_parameter_f)), 2)
        self.assertEqual(len(self._request(search_query_parameter_g)), 0)

        # postprocessing searches
        search_query_postproc_1 = {'parameter': "postproc_x,0,0"}
        search_query_postproc_2 = {'parameter': "postproc_x,0,0.5"}
        search_query_postproc_3 = {'parameter': "postproc_x,0.5,1"}
        search_query_postproc_4 = {'parameter': "postproc_x,0,1"}
        search_query_postproc_5 = {'parameter': "postproc_y,0,1"}

        self.assertEqual(len(self._request(search_query_postproc_1)), 0)
        self.assertEqual(len(self._request(search_query_postproc_2)), 1)
        self.assertEqual(len(self._request(search_query_postproc_3)), 1)
        self.assertEqual(len(self._request(search_query_postproc_4)), 2)
        self.assertEqual(len(self._request(search_query_postproc_5)), 1)

        # user searches
        search_query_users_1 = {'users': []}
        search_query_users_2 = {'users': [""]}
        search_query_users_3 = {'users': ["a"]}
        search_query_users_4 = {'users': ["1"]}
        search_query_users_5 = {'users': ["2"]}
        search_query_users_6 = {'users': ["1", "2"]}

        self.assertEqual(len(self._request(search_query_users_1)), 2)
        self.assertEqual(len(self._request(search_query_users_2)), 0)
        self.assertEqual(len(self._request(search_query_users_3)), 0)
        self.assertEqual(len(self._request(search_query_users_4)), 2)
        self.assertEqual(len(self._request(search_query_users_5)), 0)
        self.assertEqual(len(self._request(search_query_users_6)), 2)

    def test_search_hack(self):
        """
        Test search options
        """

        query = {'parameter': "hack,no-dice"}
        self.assertEqual(len(self._request(query)), 0)

        query = {'parameter': "hack,mud"}
        self.assertEqual(len(self._request(query)), 1)
        query = {'parameter': "hack,grease"}
        self.assertEqual(len(self._request(query)), 1)

        query = {'parameter': "hack"}
        self.assertEqual(len(self._request(query)), 2)

        query = {'parameter': "hack,mud,grease"}
        self.assertEqual(len(self._request(query)), 2)

        query = {'parameter': "hack,mud,grease,more"}
        self.assertEqual(len(self._request(query)), 2)

    def _request(self, query):
        url = reverse('scene-list')
        self.client.login(username='bar', password='secret')
        response = self.client.get(url, query, format='json')
        return response.data


class ScenarioTestCase(APITestCase):
    """
    ScenarioTestCase
    Tests the Scenario Django REST API
    """

    def setUp(self):
        # create Users and assign permissions
        self.user_foo = User.objects.create_user(
            username="foo",
            password="secret"
        )
        self.user_bar = User.objects.create_user(
            username="bar",
            password="secret"
        )
        for user in [self.user_foo, self.user_bar]:
            for perm in ['view_scenario', 'add_scenario',
                         'change_scenario', 'delete_scenario']:
                user.user_permissions.add(
                    Permission.objects.get(codename=perm))

        # create Scene instance and assign permissions for user_foo
        self.template = Template.objects.create(
            name="Test template",
        )
        self.scenario = Scenario.objects.create(
            name="Test main workflow",
            owner=self.user_foo,
            template=self.template,
        )
        for perm in ['view_scenario', 'add_scenario',
                     'change_scenario', 'delete_scenario']:
            assign_perm(perm, self.user_foo, self.scenario)

    def test_scenario_get(self):
        # detail view
        url = reverse('scenario-detail', args=[self.scenario.pk])

        # foo can see
        self.client.login(username='foo', password='secret')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # bar cannot see
        self.client.login(username='bar', password='secret')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_scenario_post(self):
        # list view for POST (create new)
        url = reverse('scenario-list')

        # foo can create
        self.client.login(username='foo', password='secret')
        data = {
            "name": "New Scenario 1",
            "scene_set": [],
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # bar can create
        self.client.login(username='bar', password='secret')
        data = {
            "name": "New Scenario 2",
            "scene_set": [],
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_scenario_put(self):
        # detail view for PUT (udpate)
        url = reverse('scenario-detail', args=[self.scenario.pk])

        # foo can update
        self.client.login(username='foo', password='secret')
        data = {
            "name": "New Scenario (Updated)",
            "scene_set": [],
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # bar cannot update
        self.client.login(username='bar', password='secret')
        data = {
            "name": "New Scenario (Updated)",
            "scene_set": [],
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('delft3dworker.models.Scenario.start', autospec=True)
    def test_scenario_start(self, mocked_scene_method):
        # start view
        url = reverse('scenario-start', args=[self.scenario.pk])

        # bar cannot see
        self.client.login(username='bar', password='secret')
        response = self.client.put(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(mocked_scene_method.call_count, 0)

        # foo can start
        self.client.login(username='foo', password='secret')

        response = self.client.put(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_scene_method.assert_called_with(
            self.scenario, self.user_foo)


class ScenarioSearchTestCase(TestCase):
    """
    SceneSearchTestCase
    Tests the Scene search functionality using Django REST filters


    """

    def setUp(self):
        self.user_bar = User.objects.create_user(
            username='bar',
            password='secret'
        )

        self.template = Template.objects.create(name="Template 1")

        self.scenario_1 = Scenario.objects.create(
            name='Testscenario 1',
            owner=self.user_bar,
            parameters={
                'a': {'values': [2, 3]},
                'hack': {'values': ['sand-clay', 'mud']},
            },
            scenes_parameters=[],
            template=self.template,
        )
        self.scenario_2 = Scenario.objects.create(
            name='Testscenario 2',
            owner=self.user_bar,
            parameters={
                'a': {'values': [3, 4]},
                'hack': {'values': ['sand-clay', 'grease']},
            },
            scenes_parameters=[],
            template=self.template,
        )
        self.scenario_3 = Scenario.objects.create(
            name='Empty',
            owner=self.user_bar,
            parameters={},
            scenes_parameters=[],
            template=Template.objects.create(name="Template Empty"),
        )
        self.scenario_4 = Scenario.objects.create(
            name='Wrong',
            owner=self.user_bar,
            parameters={'a': {'info': 'something_wrong'}},
            scenes_parameters=[],
            template=Template.objects.create(name="Template Empty"),
        )

        # Object general
        assign_perm('view_scenario', self.user_bar, self.scenario_1)
        assign_perm('view_scenario', self.user_bar, self.scenario_2)
        assign_perm('view_scenario', self.user_bar, self.scenario_3)
        assign_perm('view_scenario', self.user_bar, self.scenario_4)

        # Model general
        self.user_bar.user_permissions.add(
            Permission.objects.get(codename='view_scenario'))
        self.user_bar.user_permissions.add(
            Permission.objects.get(codename='view_scene'))

        # Refetch to empty permissions cache
        self.user_bar = User.objects.get(pk=self.user_bar.pk)

    def test_search_search(self):
        """
        Test search options
        """

        query = {'search': "DoesNotExist"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'search': "1"}
        self.assertEqual(len(self._request(query)), 4)
        query = {'search': "2"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'search': "es"}
        self.assertEqual(len(self._request(query)), 4)

    def test_search_name(self):
        """
        Test search options
        """

        query = {'name': "Testscenario 0"}
        self.assertEqual(len(self._request(query)), 0)

        query = {'name': "Testscenario 1"}
        self.assertEqual(len(self._request(query)), 1)
        query = {'name': "Testscenario 2"}
        self.assertEqual(len(self._request(query)), 1)

        query = {'name': "Testscenario"}
        self.assertEqual(len(self._request(query)), 0)

    def test_search_template(self):
        """
        Test search options
        """

        query = {'template': "Template 1"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'template': "Template 2"}
        self.assertEqual(len(self._request(query)), 4)

    def test_search_param(self):
        """
        Test search options
        """

        query = {'parameter': "anything"}
        self.assertEqual(len(self._request(query)), 4)

    def test_search_param_val(self):
        """
        Test search options
        """

        query = {'parameter': "anything,1"}
        self.assertEqual(len(self._request(query)), 4)

    def test_search_param_valrange(self):
        """
        Test search options
        """

        query = {'parameter': "a,0,1"}
        self.assertEqual(len(self._request(query)), 4)
        query = {'parameter': "a,0,1.9999"}
        self.assertEqual(len(self._request(query)), 4)
        query = {'parameter': "a,5,6"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'parameter': "a,1,2"}
        self.assertEqual(len(self._request(query)), 4)
        query = {'parameter': "a,1.0,2"}
        self.assertEqual(len(self._request(query)), 4)
        query = {'parameter': "a,1,2.01"}
        self.assertEqual(len(self._request(query)), 4)
        query = {'parameter': "a,1.00,2.01"}
        self.assertEqual(len(self._request(query)), 4)
        query = {'parameter': "a,4,5"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'parameter': "a,1,5"}
        self.assertEqual(len(self._request(query)), 4)

    def test_search_hack(self):
        """
        Test search options
        """

        query = {'parameter': "hack,grease"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'parameter': "hack"}
        self.assertEqual(len(self._request(query)), 4)
        query = {'parameter': "hack,sand-clay"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'parameter': "hack,mud,grease"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'parameter': "hack,mud,grease,more"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'parameter': "hack,no-dice"}
        self.assertEqual(len(self._request(query)), 4)

        query = {'parameter': "hack,mud"}
        self.assertEqual(len(self._request(query)), 4)

    def _request(self, query):
        url = reverse('scenario-list')
        self.client.login(username='bar', password='secret')
        response = self.client.get(url, query, format='json')
        return response.data


class UserTestCase(TestCase):
    """
    Test Custom User query
    """

    def setUp(self):

        # create user in dB
        self.user_foo = User.objects.create_user(
            username="foo",
            first_name="Foo",
            last_name="Oof",
            email="foo@company.nl"
        )
        groups_foo = Group.objects.create(name="org:Foo_Company")
        groups_foo.user_set.add(self.user_foo)

        self.factory = APIRequestFactory()

    def test_me(self):
        view = UserViewSet.as_view({'get': 'list'})
        request = self.factory.get('/users/me/')
        force_authenticate(request, user=self.user_foo)
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, "foo")
        self.assertContains(response, "Foo")
        self.assertContains(response, "Oof")
        self.assertContains(response, "foo@company.nl")
