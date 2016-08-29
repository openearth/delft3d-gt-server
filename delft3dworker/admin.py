from django.contrib import admin

from guardian.admin import GuardedModelAdmin

from models import Scenario
from models import Scene
from models import Container
from models import SearchForm
from models import Template


class ContainerInline(admin.StackedInline):
    extra = 0
    model = Container


@admin.register(Scenario)
class ScenarioAdmin(GuardedModelAdmin):
    pass


@admin.register(Scene)
class SceneAdmin(GuardedModelAdmin):
    inlines = [
        ContainerInline,
    ]


@admin.register(Container)
class ContainerAdmin(GuardedModelAdmin):
    pass


@admin.register(SearchForm)
class SearchFormAdmin(GuardedModelAdmin):
    pass


@admin.register(Template)
class TemplateAdmin(GuardedModelAdmin):
    pass
