from __future__ import absolute_import

from django.test import Client, TestCase
from mock import Mock

from django.contrib.admin.sites import AdminSite

from delft3dworker.models import Scene
from delft3dworker.admin import SceneAdmin



class AdminTest(TestCase):

    def setUp(self):
            self.scene_a = Scene.objects.create(
                name='Scene A',
                phase=Scene.phases.new
            )

            self.scene_b = Scene.objects.create(
                name='Scene B',
                phase=Scene.phases.fin
            )

            self.scene_admin = SceneAdmin(Scene, AdminSite())

    def test_resync(self):
            """
            Test resync scenes. Only scenes in finished state should be resynced
            """
            self.p = self.scene_a.phases
            request = Mock()
            queryset = Scene.objects.all()
            self.scene_admin.resync(request, queryset)
            print('1----- ', self.scene_a.phase)
            print('2----- ', self.p.new)
            print('3----- ', self.scene_b.phase)
            print('4----- ', self.p.sync_create)
            # self.assertEqual(self.scene_a.phase = p.new)

