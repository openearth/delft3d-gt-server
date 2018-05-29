from __future__ import absolute_import

import datetime

from mock import Mock
from mock import MagicMock
from mock import patch

from django.contrib.auth.models import Permission
from django.contrib.admin.sites import AdminSite
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

from delft3dworker.models import Group
from delft3dworker.models import User
from delft3dworker.models import Scene
from delft3dworker.models import Container
from delft3dworker.admin import SceneAdmin
from delft3dworker.admin import GroupUsageSummaryAdmin
from delft3dworker.admin import UserUsageSummaryAdmin


# from .views import


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
        self.assertEqual(Scene.objects.get(id=1).phase,
                         Scene.phases.sync_create)


class GroupUsageSummaryAdminTest(TestCase):
    def setUp(self):
        # self.client = Client()
        self.factory = RequestFactory()

        self.user_a = User.objects.create_user(username='User A')

        self.user_b = User.objects.create_user(username='User B')
        self.superuser = User.objects.create_superuser(
            username='super', password='secret', email='super@example.com')

        company_a = Group.objects.create(name='access:org:Company A')
        company_a.user_set.add(self.user_a)
        company_b = Group.objects.create(name='access:org:Company B')
        company_b.user_set.add(self.user_b)

        self.scene_a = Scene.objects.create(
            id=0,
            name='Scene A',
            owner=self.user_a
        )
        self.container_a = Container.objects.create(
            scene=self.scene_a,
            container_type='Container A',
            container_starttime=datetime.datetime(
                2010, 10, 10, 10, 10, 00, tzinfo=timezone.utc),
            container_stoptime=datetime.datetime(
                2010, 10, 10, 10, 20, 00, tzinfo=timezone.utc)
        )

        self.scene_b = Scene.objects.create(
            id=1,
            name='Scene B',
            owner=self.user_b
        )
        self.container_a = Container.objects.create(
            scene=self.scene_b,
            container_type='Container B',
            container_starttime=datetime.datetime(
                2010, 10, 10, 10, 20, 00, tzinfo=timezone.utc),
            container_stoptime=datetime.datetime(
                2010, 10, 10, 10, 40, 00, tzinfo=timezone.utc)
        )

        self.group_usage_summary_admin = GroupUsageSummaryAdmin(
            Group, AdminSite())

    def test_changelist_view(self):
        """
        Test changelist_view
        """
        factory = RequestFactory()
        request = factory.get(reverse('admin:delft3dworker_groupusagesummary_changelist'))
        request.user = self.superuser
        response = self.group_usage_summary_admin.changelist_view(request)

        summary_total = response.context_data['summary_total']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(summary_total['num_users'], 2)
        self.assertEqual(summary_total['num_containers'], 2)
        self.assertEqual(summary_total['sum_runtime'], datetime.timedelta(minutes=30))
