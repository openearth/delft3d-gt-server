from __future__ import absolute_import
import os

from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import F
from django.db.models import Sum
from django.db.models import Count
from django.db.models import ExpressionWrapper
from django.db.models import DurationField

from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter

from guardian.admin import GuardedModelAdmin

from .models import Scenario
from .models import Scene
from .models import Workflow
from .models import Version_Docker
from .models import SearchForm
from .models import Template
from .models import GroupUsageSummary
from .models import UserUsageSummary


class WorkflowInline(admin.StackedInline):
    extra = 0
    model = Workflow


class SceneInline(admin.StackedInline):
    extra = 0
    model = Scene


class VersionInline(admin.StackedInline):
    extra = 0
    model = Version_Docker


@admin.register(Scenario)
class ScenarioAdmin(GuardedModelAdmin):
    pass


@admin.register(Scene)
class SceneAdmin(GuardedModelAdmin):
    inlines = [
        WorkflowInline,
    ]

    actions = ['check_sync']

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


@admin.register(Workflow)
class WorkflowAdmin(GuardedModelAdmin):
    pass


@admin.register(Version_Docker)
class VersionAdmin(GuardedModelAdmin):
    pass


@admin.register(SearchForm)
class SearchFormAdmin(GuardedModelAdmin):
    pass


@admin.register(Template)
class TemplateAdmin(GuardedModelAdmin):
    extra = 0
    inlines = [
        VersionInline,
    ]


@admin.register(GroupUsageSummary)
class GroupUsageSummaryAdmin(admin.ModelAdmin):
    """
    # Following example available at:
    # https://medium.com/@hakibenita/how-to-turn-django-admin-into-a-lightweight-dashboard-a0e0bbf609ad
    """
    change_list_template = 'delft3dworker/group_summary_change_list.html'
    # Filter by time period
    list_filter = (('user__scene__workflow__stoptime', DateRangeFilter),)

    def changelist_view(self, request, extra_context=None):
        """
        Displays summary of usage organized by group
        """
        response = super(GroupUsageSummaryAdmin, self).changelist_view(
            request,
            extra_context=extra_context,
        )
        try:
            qs = response.context_data['cl'].queryset
            # Exclude Groups with world access as they will be counted twice in totals
            qs = qs.exclude(name='access:world').order_by('name')
        except (AttributeError, KeyError) as e:
            return response
        # Summarize by group values
        values = ['name', 'id']
        # Sum the total runtime.
        # Runtime is considered the difference in time between the start and stop time
        # of a workflow.
        metrics = {
            'num_users': Count('user__username', distinct=True),
            'sum_runtime': ExpressionWrapper(
                Sum(F('user__scene__workflow__stoptime') -
                    F('user__scene__workflow__starttime')),
                output_field=DurationField()
            ),
        }
        # Content for table
        response.context_data['summary'] = list(
            qs.values(*values)
                .annotate(**metrics)
        )
        # Content for totals in table
        response.context_data['summary_total'] = dict(
            qs.aggregate(**metrics)
        )

        return response


@admin.register(UserUsageSummary)
class UserUsageSummaryAdmin(admin.ModelAdmin):
    change_list_template = 'delft3dworker/user_summary_change_list.html'
    # Filter by time period
    list_filter = (('scene__workflow__stoptime', DateRangeFilter),)

    def changelist_view(self, request, extra_context=None):
        """
        Display summary of usage organized by users in a group
        """

        response = super(UserUsageSummaryAdmin, self).changelist_view(
            request,
            extra_context=extra_context,
        )
        try:
            qs = response.context_data['cl'].queryset
            qs = qs.order_by('username')

        except (AttributeError, KeyError) as e:
            return response
        # Summarize by user values, display group name
        values = ['username', 'groups__name']
        # Sum the total runtime.
        # Runtime is considered the difference in time between the start and stop time
        # of a workflow.
        metrics = {
            'sum_runtime': ExpressionWrapper(
                Sum(F('scene__workflow__stoptime') -
                    F('scene__workflow__starttime')),
                output_field=DurationField()
            ),
        }
        # Content for table
        response.context_data['summary'] = list(
            qs.values(*values)
                .annotate(**metrics)
        )
        # Content for totals in table
        response.context_data['summary_total'] = dict(
            qs.aggregate(**metrics)
        )

        return response
