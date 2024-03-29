from __future__ import absolute_import

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.test.client import Client
from guardian.shortcuts import assign_perm
from delft3dworker.models import Scene


class ProctectedServicesTestCase(TestCase):
    def setUp(self):
        # set up client
        self.client = Client()

        # create users and store for later access
        self.user_foo = User.objects.create_user(username="foo", password="secret")

        # create user with restricted permissions
        self.user_bar = User.objects.create_user(username="bar", password="secret")

        # create Scene instance and assign permissions for user_foo
        self.scene = Scene.objects.create(
            suid="1be8dcc1-cf00-418c-9920-efa07b4fbeca",
            name="Test main workflow 1",
            owner=self.user_foo,
            shared="p",
            phase=Scene.phases.fin,
        )

        # Add permissions to foo user
        assign_perm("extended_view_scene", self.user_foo, self.scene)
        assign_perm("view_scene", self.user_foo, self.scene)

        # create Scene instance and assign permission for user bar
        self.scene2 = Scene.objects.create(
            suid="8bfdf64a-dc3f-4f48-9bf6-507c2b4e4bd9",
            name="Test workflow 2",
            owner=self.user_bar,
            shared="w",
            phase=Scene.phases.fin,
        )

        # Add permissions to bar user
        assign_perm("view_scene", self.user_bar, self.scene2)

    def test_files(self):
        # login as foo
        self.client.login(username="foo", password="secret")

        loc = "test"
        simulation_uuid = "1be8dcc1-cf00-418c-9920-efa07b4fbeca"
        response = self.client.get("/files/{0}/{1}".format(simulation_uuid, loc))

        # /files/* should redirect to /protected_files/*
        self.assertEqual(
            response["X-Accel-Redirect"],
            "/protected_files/{0}/{1}".format(simulation_uuid, loc),
        )
        self.assertEqual(response.status_code, 200)

    def test_files_restricted_view(self):
        # login as bar
        self.client.login(username="bar", password="secret")

        # In restricted view it is only allowed to view png images
        loc1 = "test"
        loc2 = "test/image.png"

        simulation_uuid = "8bfdf64a-dc3f-4f48-9bf6-507c2b4e4bd9"
        response1 = self.client.get("/files/{0}/{1}".format(simulation_uuid, loc1))
        response2 = self.client.get("/files/{0}/{1}".format(simulation_uuid, loc2))

        self.assertEqual(response1.status_code, 403)
        self.assertEqual(response2.status_code, 200)

    def test_thredds(self):
        # login as foo
        # foo has view permissions and is allowed to view thredds files
        self.client.login(username="foo", password="secret")

        loc = "test"
        simulation_uuid = "1be8dcc1-cf00-418c-9920-efa07b4fbeca"
        response = self.client.get(
            "/thredds/catalog/files/{0}/{1}".format(simulation_uuid, loc)
        )
        # /files/* should redirect to /protected_files/*
        self.assertEqual(
            response["X-Accel-Redirect"],
            "/protected_thredds/catalog/files/{0}/{1}?".format(simulation_uuid, loc),
        )
        self.assertEqual(response.status_code, 200)

        # login as bar
        # bar has only restricted view permissions and is not allowed to view thredds files
        self.client.login(username="bar", password="secret")
        response = self.client.get(
            "/thredds/catalog/files/{0}/{1}".format(simulation_uuid, loc)
        )
        self.assertEqual(response.status_code, 403)

    def test_thredds_static(self):
        # login as foo
        self.client.login(username="foo", password="secret")

        loc = "test"
        response = self.client.get("/thredds/{0}?a=1&b=2".format(loc))
        # /thredds/* should redirect to /protected_thredds/*
        self.assertEqual(
            response["X-Accel-Redirect"], "/protected_thredds/{0}?a=1&b=2".format(loc)
        )
        self.assertEqual(response.status_code, 200)
