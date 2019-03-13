from __future__ import absolute_import

import datetime

from mock import Mock

from django.contrib.auth.models import Permission
from django.contrib.admin.sites import AdminSite
from django.test import Client, TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

from delft3dworker.models import Group
from delft3dworker.models import User
from delft3dworker.models import Scene
from delft3dworker.models import Container
from delft3dworker.admin import SceneAdmin
from delft3dworker.admin import GroupUsageSummaryAdmin


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
        self.factory = RequestFactory()

        self.user_a = User.objects.create_user(username='User A')
        self.user_b = User.objects.create_user(username='User B')
        self.superuser = User.objects.create_superuser(
            username='super', password='secret', email='super@example.com')

        self.company_w = Group.objects.create(name='access:world')
        for user in [self.user_a, self.user_b]:
            self.company_w.user_set.add(user)
            for perm in ['view_scene', 'add_scene',
                         'change_scene', 'delete_scene']:
                user.user_permissions.add(
                    Permission.objects.get(codename=perm)
                )
        self.company_a = Group.objects.create(name='access:org:Company A')
        self.company_a.user_set.add(self.user_a)
        self.company_b = Group.objects.create(name='access:org:Company B')
        self.company_b.user_set.add(self.user_b)

        self.scene_a = Scene.objects.create(
            id=0,
            name='Scene A',
            owner=self.user_a
        )
        self.scene_b = Scene.objects.create(
            id=1,
            name='Scene B',
            owner=self.user_b
        )

        self.container_a = Container.objects.create(
            scene=self.scene_a,
            container_type='Container A',
            container_starttime=datetime.datetime(
                2010, 10, 10, 10, 10, 00, tzinfo=timezone.utc),
            container_stoptime=datetime.datetime(
                2010, 10, 10, 10, 20, 00, tzinfo=timezone.utc)
        )
        self.container_b = Container.objects.create(
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
        Test changelist_view for correct summaries
        """
        factory = RequestFactory()
        request = factory.get(reverse('admin:delft3dworker_groupusagesummary_changelist'))
        request.user = self.superuser
        response = self.group_usage_summary_admin.changelist_view(request)

        summary_total = response.context_data['summary_total']

        # Totals should be 2 users, 2 containers, and 30 min total runtime
        self.assertEqual(response.status_code, 200)
        self.assertEqual(summary_total['num_users'], 2)
        self.assertEqual(summary_total['num_containers'], 2)
        self.assertEqual(summary_total['sum_runtime'], datetime.timedelta(minutes=30))
