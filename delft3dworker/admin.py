import os

from django import forms
from django.forms import ModelForm
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.admin import DateFieldListFilter
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import F
from django.db.models import Sum
from django.db.models import Count
from django.db.models import ExpressionWrapper
from django.db.models import DurationField
from django.http import HttpResponseRedirect

from guardian.admin import GuardedModelAdmin

from models import Group
from models import Scenario
from models import Scene
from models import Container
from models import SearchForm
from models import Template
from models import Version_SVN
from models import GroupUsageSummary
from models import UserUsageSummary


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

@admin.register(GroupUsageSummary)
class GroupUsageSummaryAdmin(admin.ModelAdmin):
    # Following example available at:
    # https://medium.com/@hakibenita/how-to-turn-django-admin-into-a-lightweight-dashboard-a0e0bbf609ad

    change_list_template = 'delft3dworker/group_summary_change_list.html'
    # Sort by time period
    date_hierarchy = 'user__scene__container__container_stoptime'
    list_filter = (('user__scene__container__container_stoptime', DateFieldListFilter),)
    startdate = AdminDateWidget()
    enddate = AdminDateWidget()

    # https://stackoverflow.com/questions/1668220/filtering-by-custom-date-range-in-django-admin
    # Need to redirect to url of form:
    # /admin/delft3dworker/groupusagesummary/?user__scene__container__container_stoptime__gte=
    # 2018-03-01&user__scene__container__container_stoptime__lt=2018-06-01
    # def date_redirect(request):
    #     url = '/user__scene__container__container_stoptime__gte=%s&user__scene__container__container_stoptime__lt=%s' % (request.startdate, request.enddate)
    #     return HttpResponseRedirect(url)

    # I think I might need a custom form
    # https://stackoverflow.com/questions/32892847/add-calendar-widget-to-django-form

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
            # All user belong to world. To avoid double counting run_time we exclude this group
            # Then order by the group name to sort
            qs = qs.exclude(name='access:world').order_by('name')#.filter(user__scene__container__container_stoptime__range=[startdate, enddate])


        except (AttributeError, KeyError) as e:
            return response
        # Summarize by group values
        values = ['name', 'id']
        # Count the users and containers per group, and sum total runtime.
        # Runtime is considered the difference in time between the start and stop time
        # of a container.
        metrics = {
            'num_users': Count('user__username', distinct=True),
            'num_containers': Count('user__scene__container', distinct=True),
            'sum_runtime': ExpressionWrapper(
                Sum(F('user__scene__container__container_stoptime') -
                    F('user__scene__container__container_starttime')),
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
    # Sort by time period
    date_hierarchy = 'scene__container__container_stoptime'
    # Provide options for filtering by group and time
    list_filter = ('groups__name', 'scene__container__container_stoptime')

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
        # Count the containers per user, and sum total runtime.
        # Runtime is considered the difference in time between the start and stop time
        # of a container.
        metrics = {
            'num_containers': Count('scene__container', distinct=True),
            'sum_runtime': ExpressionWrapper(
                Sum(F('scene__container__container_stoptime') -
                    F('scene__container__container_starttime')),
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
