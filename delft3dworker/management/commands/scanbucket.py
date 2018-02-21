from __future__ import absolute_import
from django.core.management import BaseCommand

from delft3dworker.models import Scene

"""
File scan command that's called periodically.
- Loop over container models that are finished
- Call local scan functions of those scenes

Because of cloud simulations files are not local
anymore and arrive after a delay.
In this way, (post)processing output is added
to the database (thus frontend) even after a model
is finished. 
"""


class Command(BaseCommand):
    help = "scan local files for finished models and update models"

    def handle(self, *args, **options):

        # STEP I : Find finished models
        fin_scenes = Scene.objects.filter(phase=Scene.phases.fin)

        # STEP II : Call local scan
        for scene in fin_scenes:
            scene._local_scan_process()  # update images and logfile
            scene._local_scan_postprocess()  # scan for new images
            scene._parse_postprocessing()  # parse output.ini
