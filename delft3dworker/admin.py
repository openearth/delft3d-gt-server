import os
import logging
import datetime

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import F
from django.db.models import Sum
from django.db.models import Count
from django.db.models import ExpressionWrapper
from django.db.models import DateTimeField
from django.db.models import DurationField
from django.db.models.functions import Trunc

from guardian.admin import GuardedModelAdmin

from models import Scenario
from models import Scene
from models import Container
from models import SearchForm
from models import Template
from models import Version_SVN
from models import UsageSummary

from delft3dworker.utils import tz_now

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
    date_hierarchy = 'scene__date_started'
    list_filter = ('groups__name','groups__id','scene__date_started')

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
            qs.order_by('groups__name')

        except (AttributeError, KeyError) as e:
            print(e)
            return response

        cost_per_second = 0.01
        values = ['username', 'groups__name']
        metrics = {
            # 'num_users': Count('user'),
            'num_containers': Count('scene__container', distinct=True),
            'sum_runtime': ExpressionWrapper(
                Sum(F('scene__container__container_stoptime') \
                    - F('scene__container__container_starttime')), output_field=DurationField()
            ),
        }

        response.context_data['summary'] = list(
            qs.values(*values)
            .annotate(**metrics)
            # .annotate(est_cost=F('sum_runtime').total_seconds()*cost_per_second)
        )

        response.context_data['summary_total'] = dict(
            qs.aggregate(**metrics)
        )

        # summary_over_time = qs.annotate(
        #     period=Trunc(
        #         'scene__date_started',
        #         'day',
        #         output_field=DateTimeField(default=tz_now, blank=True),
        #     ),
        # ).values('period')
        # print(summary_over_time)
        # .annotate(
        #     total=Sum(F('scene__container__container_stoptime') - F('scene__container__container_starttime')),
        # )
        # .order_by('period')
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