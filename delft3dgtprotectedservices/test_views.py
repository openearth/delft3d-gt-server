from __future__ import absolute_import
from django.contrib.auth.models import User, Permission
from django.test.client import Client
from django.test import TestCase

from guardian.shortcuts import assign_perm

from delft3dworker.models import Scene


class ProctectedServicesTestCase(TestCase):

    def setUp(self):
        # set up client
        self.client = Client()

        # create users and store for later access
        self.user_foo = User.objects.create_user(
            username='foo', password="secret")

        # create Scene instance and assign permissions for user_foo
        self.scene = Scene.objects.create(
            suid="1be8dcc1-cf00-418c-9920-efa07b4fbeca",
            name="Test main workflow 1",
            owner=self.user_foo,
            shared="p",
            phase=Scene.phases.fin
        )

        self.user_foo.user_permissions.add(
            Permission.objects.get(codename='view_scene'))
        assign_perm('view_scene', self.user_foo, self.scene)

    def test_files(self):
        # login as foo
        self.client.login(username='foo', password='secret')

        loc = 'test'
        simulation_uuid = '1be8dcc1-cf00-418c-9920-efa07b4fbeca'
        response = self.client.get("/files/{0}/{1}".format(
        simulation_uuid, loc))
        # /files/* should redirect to /protected_files/*
        self.assertEqual(response["X-Accel-Redirect"], "/protected_files/{0}/{1}".format(simulation_uuid, loc))
        self.assertEqual(response.status_code, 200)

    def test_thredds(self):
        # login as foo
        self.client.login(username='foo', password='secret')

        loc = 'test'
        simulation_uuid = '1be8dcc1-cf00-418c-9920-efa07b4fbeca'
        response = self.client.get("/thredds/catalog/files/{0}/{1}".format(
        simulation_uuid, loc))
        # /files/* should redirect to /protected_files/*
        self.assertEqual(response["X-Accel-Redirect"], "/protected_thredds/catalog/files/{0}/{1}?".format(simulation_uuid, loc))
        self.assertEqual(response.status_code, 200)

    def test_thredds_static(self):
        # login as foo
        self.client.login(username='foo', password='secret')

        loc = 'test'
        response = self.client.get("/thredds/{0}?a=1&b=2".format(loc))
        # /thredds/* should redirect to /protected_thredds/*
        self.assertEqual(response["X-Accel-Redirect"], "/protected_thredds/{0}?a=1&b=2".format(loc))
        self.assertEqual(response.status_code, 200)
