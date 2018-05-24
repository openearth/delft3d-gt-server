from __future__ import absolute_import

import datetime

from mock import Mock
from mock import patch


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


class UserUsageSummaryAdminTest(TestCase):
    def setUp(self):
            self.client = Client()
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

            self.user_usage_summary_admin = UserUsageSummaryAdmin(User, AdminSite())

    # @patch('delft3dworker.admin.UsageSummaryAdmin.changelist_view')
    def test_changelist_view(self):
            """
            Test changelist_view scenes. Only scenes in finished state should be resynced
            """
            # response = self.client.post(reverse(),)c.get('/admin/delft3dworker/usagesummary/')
            # c.post('',)
            # request = mocked_usage_summary()
            # request.changelist_view.return_value = [{}]
            # response = request.changelist_view()
            # self.assertIsNotNone(response)
            request = Mock()
            queryset = User.objects.all()
            response = self.user_usage_summary_admin.changelist_view()

            self.assertEqual(response.status_code, 200)
            # self.assertEqual(len(response.context['summary']), 2)
            # datetime.timedelta(minutes=10))
            # self.assertEqual(response.context['summary_total__sum_runtime'], datetime.timedelta(minutes=20))
            # self.assertEqual(response.context[], datetime.timedelta(minutes=30))
            # self.assertEqual(response.context[], 2)
            # self.assertEqual(response.context[groups], 2)
