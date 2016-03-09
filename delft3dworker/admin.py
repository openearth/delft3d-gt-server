from django.contrib import admin

from models import Delft3DWorker
from models import Scene
from models import ProcessingTask
from models import SimulationTask


admin.site.register(Delft3DWorker)
admin.site.register(Scene)
admin.site.register(ProcessingTask)
admin.site.register(SimulationTask)