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

        # Loop over non empty celery_task_ids in containers
        # celery_set = set(
        #     Container.objects.exclude(celery_id__exact='').values_list('celery_id', flat=True))

        # retrieve containers from docker
        containers_docker = get_docker_ps()
        docker_set = set([container_docker['Id']
                          for container_docker in containers_docker])

        # retrieve container from database
        container_set = set(
            Container.objects.values_list('docker_id', flat=True))

        # loop over database container and lookup matching containers
        # Stop the orphan container and call update state for others

        m_1_1 = docker_set & container_set
        m_1_0 = container_set - docker_set
        m_0_1 = docker_set - container_set
        m_0_0 = ((docker_set | container_set) -
                 (docker_set ^ container_set) -
                 (docker_set & container_set)
                 )

        # All matching containers
        container_match = m_1_1 | m_1_0

        # Call error for mismatch
        container_mismatch = m_0_1 | m_0_0
        #
        # for container in container_match:
        #     Container(id=container)._update_state_and_save()

        # loop over scene and call update_state()
        