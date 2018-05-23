from __future__ import absolute_import

from mock import Mock

from django.contrib.admin.sites import AdminSite
from django.test import Client, TestCase

from delft3dworker.models import Scene
from delft3dworker.admin import SceneAdmin


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
            self.scene_a = Scene.objects.create(
                id=0,
                name='Scene A',
                phase=Scene.phases.new
            )

            self.container_a = Container.objects.create(
                container_type = 'Container A',
                container_starttime = datetime.datetime(2010, 10, 10, 10, 10, 00),
                container_stoptime = datetime.datetime(2010, 10, 10, 10, 20, 00)
            )

            self.scene_b = Scene.objects.create(
                id=1,
                name='Scene B',
                phase=Scene.phases.fin
            )
            self.container_a = Container.objects.create(
                container_type='Container A',
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
            self.usage_summary(request, queryset)

            # scene_a should still be new
            # scene_b should be in sync_create
            self.assertEqual(Scene.objects.get(id=0).phase, )
            self.assertEqual(Scene.objects.get(id=1).phase, )