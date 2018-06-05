import os

from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings

from guardian.admin import GuardedModelAdmin

from models import Scenario
from models import Scene
from models import Workflow
from models import SearchForm
from models import Template


class WorkflowInline(admin.StackedInline):
    extra = 0
    model = Workflow


class SceneInline(admin.StackedInline):
    extra = 0
    model = Scene


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


@admin.register(SearchForm)
class SearchFormAdmin(GuardedModelAdmin):
    pass


@admin.register(Template)
class TemplateAdmin(GuardedModelAdmin):
    pass

