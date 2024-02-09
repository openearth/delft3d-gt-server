import logging

from django.core.management import BaseCommand

from delft3dworker.models import Scene, Workflow

"""
Script to migrate legacy scenes:
- Adds workflows to scenes without
- Corrects non-existing phases to existing ones

The new kubernetes architecture has two new models,
while the old svn model is gone. Migrating the legacy
production database involves:
- Run migrations
- Add shortname and yaml file to template
- Run this script
- Start models where applicable
"""

logging.getLogger().setLevel(logging.INFO)


class Command(BaseCommand):
    help = "Scan for old Scenes and update them to the new ET architecture."

    def handle(self, *args, **options):
        # STEP I : Find scenes without a workflow
        legacy_scenes = Scene.objects.filter(workflow=None)

        # STEP II : Call local scan
        for scene in legacy_scenes:
            if scene.scenario.first() is None:
                logging.warning("Scene {} has no scenario!".format(scene.id))
                continue

            # reset info field and scan for files again
            scene.info = scene.scenario.first().template.info
            scene._local_scan_files()
            scene.info.update({"legacy": True})  # help debugging in the future
            scene.save()

            logging.info("Add workflow to scene {}.".format(scene.id))
            workflow = Workflow.objects.create(
                scene=scene,
                name="{}-{}".format(
                    scene.scenario.first().template.shortname, scene.suid
                ),
                progress=scene.progress,
                version=scene.scenario.first().template.versions.first(),  # latest
            )
            workflow.save()

        for scene in Scene.objects.all():
            if scene.phase not in Scene.phases:
                logging.info("Migrating {} to idle.".format(scene.id))
                scene.shift_to_phase(Scene.phases.idle)
