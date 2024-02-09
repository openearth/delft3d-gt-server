from os import walk
from os.path import join
from shutil import rmtree

from django.conf import settings
from django.core.management.base import BaseCommand

from delft3dworker.models import Scene


class Command(BaseCommand):
    help = "Removes leftover file directories not linked to existing models."

    def handle(self, *args, **options):
        ignore = set([join(settings.WORKER_FILEDIR, "theme")])  # files styling dir
        scenedirs = [
            scene.workingdir.encode("ascii", "ignore") for scene in Scene.objects.all()
        ]
        linked = set()

        # Django workingdirs have trailing slash
        for scenedir in scenedirs:
            if scenedir[-1] == "/":
                scenedir = scenedir[:-1]
            linked.add(scenedir)

        r, d, f = next(walk(settings.WORKER_FILEDIR))
        existing = set([join(r, directory) for directory in d])

        linked = linked | ignore
        unlinked = existing - linked

        for directory in unlinked:
            try:
                rmtree(directory)
                self.stdout.write(f"Successfully deleted unlinked folder {directory}")
            except Exception as e:
                self.stdout.write(f"Couldn't delete folder {directory}: {e}")
