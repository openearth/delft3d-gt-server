from django.contrib import admin

from guardian.admin import GuardedModelAdmin

from models import Scenario
from models import Scene
from models import Template

@admin.register(Template)
class TemplateAdmin(GuardedModelAdmin):
    pass

@admin.register(Scenario)
class ScenarioAdmin(GuardedModelAdmin):
    pass

@admin.register(Scene)
class SceneAdmin(GuardedModelAdmin):
    pass
