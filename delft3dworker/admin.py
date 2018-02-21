from django.contrib import admin

from guardian.admin import GuardedModelAdmin

from models import Scenario
from models import Scene
from models import Container
from models import SearchForm
from models import Template
from models import Version_SVN


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

    actions = ['resync']

    def resync(self, request, queryset):
        """
        This action will sync EFS with S3 again.
        Use this action if objects are missing after run is finished.
        """
        rows_updated = 0
        for obj in queryset:
            if obj.phase == Scene.phases.fin:
                queryset.update(phase=Scene.phases.sync_create)
                rows_updated += 1
        self.message_user(
            request, "{} scenes successfully set to sychronization phase.".format(rows_updated))


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
