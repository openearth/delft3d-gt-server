from django.core.management import BaseCommand

from delft3dcontainermanager.tasks import get_docker_ps
from delft3dworker.models import Container

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
        # retrieve containers from docker
        containers_docker = get_docker_ps()
        container_ids = set([container_docker['Id'] for container_docker in containers_docker])

        # retrieve container from database
        containers_model = set(Container.objects.values_list('docker_id', flat=True))

        # loop over database container and lookup matching containers
        # Stop the orphan container and call update state for others
        for container_model in containers_model:

            print container_model


        # loop over scene and call update_state()