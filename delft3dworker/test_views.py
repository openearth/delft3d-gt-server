from __future__ import absolute_import

from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

from guardian.shortcuts import assign_perm

from mock import MagicMock
from mock import patch

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.views import ScenarioViewSet
from delft3dworker.views import SceneViewSet
from delft3dworker.views import UserViewSet


class ListAccessTestCase(TestCase):

    def setUp(self):

        # set up request factory
        self.factory = APIRequestFactory()

        # create users and store for later access
        self.user_foo = User.objects.create_user(username='foo')
        self.user_bar = User.objects.create_user(username='bar')

        # create models in dB
        scenario = Scenario.objects.create(
            name='Test Scenario',
            owner=self.user_foo,
        )
        a = Scene.objects.create(
            name='Test Scene 1',
            owner=self.user_foo,
            parameters={'a': {'values': 2}},
            state='SUCCESS',
            shared='p',
        )
        a.scenario.add(scenario)
        b = Scene.objects.create(
            name='Test Scene 2',
            owner=self.user_foo,
            parameters={'a': {'values': 3}},
            state='SUCCESS',
            shared='p',
        )
        b.scenario.add(scenario)

        # Model general
        self.user_foo.user_permissions.add(
            Permission.objects.get(codename='view_scenario'))
        self.user_foo.user_permissions.add(
            Permission.objects.get(codename='view_scene'))
        self.user_bar.user_permissions.add(
            Permission.objects.get(codename='view_scenario'))
        self.user_bar.user_permissions.add(
            Permission.objects.get(codename='view_scene'))

        # Object general
        assign_perm('view_scenario', self.user_foo, scenario)
        assign_perm('change_scenario', self.user_foo, scenario)
        assign_perm('delete_scenario', self.user_foo, scenario)

        assign_perm('view_scene', self.user_foo, a)
        assign_perm('change_scene', self.user_foo, a)
        assign_perm('delete_scene', self.user_foo, a)
        assign_perm('view_scene', self.user_foo, b)
        assign_perm('change_scene', self.user_foo, b)
        assign_perm('delete_scene', self.user_foo, b)

        # Refetch to empty permissions cache
        self.user_foo = User.objects.get(pk=self.user_foo.pk)
        self.user_bar = User.objects.get(pk=self.user_bar.pk)

    def test_search(self):
        """
        Tests GET access rights on list Views
        """

        # User Foo can access own models
        self.assertEqual(
            len(self._request(ScenarioViewSet, self.user_foo)),
            1
        )
        self.assertEqual(
            len(self._request(SceneViewSet, self.user_foo)),
            2
        )

        # User Bar can access no models (because Bar owns none)
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        return response.data


class SceneSearchTestCase(TestCase):

    def setUp(self):
        self.user_bar = User.objects.create_user(username='bar')
        scenario = Scenario.objects.create(
            name='Test',
            owner=self.user_bar,
        )
        self.scene = Scene.objects.create(
            name='Test',
            owner=self.user_bar,
            parameters={'a': {'value': 2}},
            state='SUCCESS',
            shared='p',
        )
        self.scene.scenario.add(scenario)
        # we do not want to test the model, only the views
        self.scene.start = MagicMock()

        # Object general
        assign_perm('view_scene', self.user_bar, self.scene)
        assign_perm('change_scene', self.user_bar, self.scene)
        assign_perm('delete_scene', self.user_bar, self.scene)

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
        search_query_exact_a = {'name': "Test"}
        search_query_exact_b = {'state': "FINISHED"}
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


class SceneTestCase(APITestCase):
    """
    Test custom written function SceneViewSet
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
        self.scene = Scene.objects.create(
            name="Test main workflow",
            owner=self.user_foo,
            shared='p',
        )
        for perm in ['view_scene', 'add_scene',
                     'change_scene', 'delete_scene']:
            assign_perm(perm, self.user_foo, self.scene)

    def test_scene_get(self):
        # detail view
        url = reverse('scene-detail', args=[self.scene.pk])

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
        url = reverse('scene-detail', args=[self.scene.pk])

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
        self.scene.publish_company(self.user_foo)

        # detail view for PUT (update)
        url = reverse('scene-detail', args=[self.scene.pk])

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

    @patch('delft3dworker.models.Scene.start')
    def test_scene_start(self, mockedMethod):
        # start view
        url = reverse('scene-start', args=[self.scene.pk])

        # bar cannot see
        self.client.login(username='bar', password='secret')
        response = self.client.put(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mockedMethod.assert_not_called()

        # foo can start, both default and with arguments
        self.client.login(username='foo', password='secret')
        response = self.client.put(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mockedMethod.assert_called_with(workflow="main")
        response = self.client.put(url, {"workflow": "test"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mockedMethod.assert_called_with(workflow="test")

    @patch('delft3dworker.models.Scene.start')
    def test_scene_no_start_after_publish(self, mockedMethod):
        # the scene is published
        self.scene.publish_company(self.user_foo)

        # start view
        url = reverse('scene-start', args=[self.scene.pk])

        # foo cannot start (forbidden)
        self.client.login(username='foo', password='secret')
        response = self.client.put(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mockedMethod.assert_not_called()


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
