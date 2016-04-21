from django.contrib import admin

from models import ProcessingTask
from models import Scenario
from models import Scene
from models import SimulationTask
from models import Template


admin.site.register(Template)
admin.site.register(Scenario)
admin.site.register(Scene)
admin.site.register(SimulationTask)
admin.site.register(ProcessingTask)
