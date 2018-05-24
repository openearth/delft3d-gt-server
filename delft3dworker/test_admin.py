from __future__ import absolute_import

import datetime

from mock import Mock

from django.contrib.admin.sites import AdminSite
from django.test import Client, TestCase

from delft3dworker.models import User
from delft3dworker.models import Scene
from delft3dworker.models import Container
from delft3dworker.admin import SceneAdmin
from delft3dworker.admin import UsageSummaryAdmin


class AdminTest(TestCase):

    def setUp(self):
            self.scene_a = Scene.objects.create(
                id=0,
                name='Scene A',
                phase=Scene.phases.new
            )

            self.scene_b = Scene.objects.create(
                id=1,
                name='Scene B',
                phase=Scene.phases.fin
            )

            self.scene_admin = SceneAdmin(Scene, AdminSite())

    def test_resync(self):
            """
            Test resync scenes. Only scenes in finished state should be resynced
            """
            request = Mock()
            queryset = Scene.objects.all()
            self.scene_admin.resync(request, queryset)

            # scene_a should still be new
            # scene_b should be in sync_create
            self.assertEqual(Scene.objects.get(id=0).phase, Scene.phases.new)
            self.assertEqual(Scene.objects.get(id=1).phase, Scene.phases.sync_create)


class UsageSummaryAdminTest(TestCase):

    def setUp(self):
            self.user_a = User.objects.create(
                username='User A'
            )

            self.scene_a = Scene.objects.create(
                id=0,
                name='Scene A',
                owner=self.user_a
            )

            self.container_a = Container.objects.create(
                scene = self.scene_a,
                container_type = 'Container A',
                container_starttime = datetime.datetime(2010, 10, 10, 10, 10, 00),
                container_stoptime = datetime.datetime(2010, 10, 10, 10, 20, 00)
            )

            self.user_b = User.objects.create(
                username='User B'
            )

            self.scene_b = Scene.objects.create(
                id=1,
                name='Scene B',
                owner = self.user_b
            )
            self.container_a = Container.objects.create(
                scene = self.scene_b,
                container_type='Container B',
                container_starttime = datetime.datetime(2010, 10, 10, 10, 20, 00),
                container_stoptime = datetime.datetime(2010, 10, 10, 10, 40, 00)
            )

            self.usage_summary_admin = UsageSummaryAdmin(Scene, AdminSite())

    def test_changelist_view(self):
            """
            Test changelist_view scenes. Only scenes in finished state should be resynced
            """
            request = Mock()
            queryset = Scene.objects.all()
            response = self.usage_summary_admin.changelist_view(request, queryset)

            # scene_a should still be new
            # scene_b should be in sync_create
            self.assertEqual(response.sum_runtime, datetime.timedelta(minutes=10))
            self.assertEqual(response, datetime.timedelta(minutes=20))
            self.assertEqual(response.summary_total.sum_runtime, datetime.timedelta(minutes=30))
            self.assertEqual(response.summary_total.num_containers, 2)
            self.assertEqual(response.summary_total.num_containers, 2)
