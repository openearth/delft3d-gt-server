from django.core.management import BaseCommand

"""
TODO: write this management command with the following functionality:

- Run docker ps (celery task)
- Loop over container models and compare with the output of docker ps
- Missing container model (orphan) -> Error, stop container
- For the other container run container.update_state(docker_ps)
- Finally loop over the scene models and call update_state()
"""


class Command(BaseCommand):
    help = "sync containers with container and scene model"

    def handle(self, *args, **options):
        self.stdout.write("containersync_sceneupdate skeleton")