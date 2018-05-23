import os
import logging

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, F, Sum

from guardian.admin import GuardedModelAdmin

from models import Scenario
from models import Scene
from models import Container
from models import SearchForm
from models import Template
from models import Version_SVN
from models import UsageSummary

class ContainerInline(admin.StackedInline):
    extra = 0
    model = Container


class SceneInline(admin.StackedInline):
    extra = 0
    model = Scene


@admin.register(Scenario)
class ScenarioAdmin(GuardedModelAdmin):
    pass


@admin.register(Scene)
class SceneAdmin(GuardedModelAdmin):
    inlines = [
        ContainerInline,
    ]

    actions = ['resync',
               'check_sync']

    def resync(self, request, queryset):
        """
        This action will sync EFS with S3 again.
        Use this action if objects are missing after run is finished.
        """
        rows_updated = queryset.filter(phase=Scene.phases.fin).update(
            phase=Scene.phases.sync_create)
        self.message_user(
            request, "{} scene(s) set to sychronization phase.".format(rows_updated))

    def check_sync(self, request, queryset):
        """
        Action to send an email with a list of all scenes with synchronization problems.
        """
        finshed_runs = queryset.filter(phase=Scene.phases.fin)
        sync_failed = []

        for obj in finshed_runs:
            sync_log = os.path.join(obj.workingdir, 'log', 'sync_cleanup.log')
            if os.path.exists(sync_log):
                if 'SYNC_STATUS' in open(sync_log).read():
                    sync_failed.append(obj.name)

        if len(sync_failed) == 0:
            subject = "Delft3D-GT: No synchronization problems"
        else:
            subject = "Delft3D-GT: Synchronization problems"

        message = ', '.join(sync_failed)
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = ["delft3d-gt@deltares.nl"]
        send_mail(subject, message, from_email, recipient_list)


@admin.register(Container)
class ContainerAdmin(GuardedModelAdmin):
    pass


@admin.register(SearchForm)
class SearchFormAdmin(GuardedModelAdmin):
    pass


@admin.register(Template)
class TemplateAdmin(GuardedModelAdmin):
    pass


@admin.register(Version_SVN)
class Version_SVN_Admin(GuardedModelAdmin):
    inlines = [
        SceneInline,
    ]


@admin.register(UsageSummary)
class UsageSummaryAdmin(admin.ModelAdmin):
    # https://medium.com/@hakibenita/how-to-turn-django-admin-into-a-lightweight-dashboard-a0e0bbf609ad

    change_list_template = 'delft3dworker/summary_change_list.html'
    # date_hierarchy = 'date_created'
    # list_filter = ('shared','owner',)

    # for g in group:
    # users = User.objects.filter(groups = group)
    # for u in users:
    # scenes = Scene.objects.filter(owner = users)
    # runtime = scenes.containers.get(F('stoptime') - F('starttime'))
    # def get_extra_context(self):
    #     group = Group.objects.filter(name='Nit_Company')
    #     users = User.objects.filter(groups=group)
    #     scenes = Scene.objects.filter(owner=users)
    #     containers = Container.objects.filter(scene=scenes).annotate(
    #         runtime=F('container_stoptime') - F('container_starttime'))
    def get_next_in_date_hierarchy(request, date_hierarchy):
        if date_hierarchy + '__day' in request.GET:
            return 'hour'
        if date_hierarchy + '__month' in request.GET:
            return 'day'
        if date_hierarchy + '__year' in request.GET:
            return 'week'
        return 'month'

    def changelist_view(self, request, extra_context=None):
        response = super(UsageSummaryAdmin, self).changelist_view(
            request,
            extra_context=extra_context,
        )
        try:
            qs = response.context_data['cl'].queryset
            qs = qs.order_by('id')
            users = User.objects.values('groups').annotate(total_users=Count('groups')).order_by('groups')
            # print(users)
            # scenes = Scene.objects.values('owner').annotate(total_scenes=Count('owner')).order_by('owner')
            # print(scenes)
            # containers = Container.objects.values('scene').annotate(
            #     runtime=F('container_stoptime') - F('container_starttime')
            # )

        except (AttributeError, KeyError) as e:
            print(e)
            return response

        values = ['name','id']
        metrics = {
            'num_users': Count('user'),
            # 'num_scenes': Count('scene')
        }

        response.context_data['summary'] = list(
            qs.values(*values)
            .annotate(**metrics)
        )
        # values = [users.username, scenes.scene, containers.container_type, containers.runtime]
        # metrics = {
        #     'total_users': Count(users.username),
        #     'total_scenes': Count(scenes.scene),
        #     'total_containers': Count(container.container_type),
        # }
        # response.context_data['summary'] = list(
        #     qs.values(*values)
        #     .annotate(**metrics)
        #     .aggregate(total_runtime = Sum(container.runtime))
        #     .order_by('-total_runtime')
        # )
        # response.context_data['summary_total'] = dict(
        #     qs.aggregate(**metrics)
        # )
        #
        # period = get_next_in_date_hierarchy(
        #     request,
        #     self.date_hierarchy,
        # )
        # response.context_data['period'] = period
        #
        # summary_over_time = qs.annotate(
        #     period=Trunc(
        #         'date_created',
        #         period,
        #         output_field=DateTimeField(),
        #     ),
        # ).values('period').aggregate(
        #     total=Sum('runtime')
        # ).order_by('period')
        #
        # summary_range = summary_over_time.aggregate(
        #     low=Min('total'),
        #     high=Max('total'),
        # )
        # high = summary_range.get('high', 0)
        # low = summary_range.get('low', 0)
        # response.context_data['summary_over_time'] = [{
        #     'period': x['period'],
        #     'total': x['total'] or 0,
        #     'pct': \
        #         ((x['total'] or 0) - low) / (high - low) * 100
        #         if high > low else 0,
        # } for x in summary_over_time]

        return response