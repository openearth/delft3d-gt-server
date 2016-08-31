import celery
import logging
from django.core.management import BaseCommand

from delft3dcontainermanager.tasks import get_docker_ps
from delft3dcontainermanager.tasks import do_docker_remove
from delft3dworker.models import Container
from delft3dworker.models import Scene

"""
Synchronization command that's called periodically.
- Run docker ps (celery task)
- Loop over container models and compare with the output of docker ps
- Missing container model (orphan) -> Error, stop container
- For the other container run container.update_state(docker_ps)
- Finally loop over the scene models and call update_state()
"""


class Command(BaseCommand):
    help = "sync containers with container and scene model"

    def handle(self, *args, **options):

        # STEP I : Loop over non empty celery_task_ids in containers
        # Sets task_uuid to None except for when a task is queued
        # Queued for log, no start? expire gebruiken
        self._update_container_tasks()

        # STEP II : Update Scenes and their Phases
        # Controls container desired states
        self._update_scene_phases()

        # STEP III : Synchronise Django Container Models and Docker containers

        self._synchronise_django_docker_containers()

    def _update_container_tasks(self):
        """
        Update Containers with results from finished tasks.
        """
        celery_set = set(Container.objects.exclude(task_uuid__exact=None))

        for container in celery_set:
            container.update_task_result()

    def _update_scene_phases(self):
        """
        Update Scenes with latest status of their Containers, and possibly
        shift Scene phase
        """

        # TODO: uncommand following lines when update_and_phase_shift is
        # available
        for scene in Scene.objects.all():
            scene.update_and_phase_shift()

    def _synchronise_django_docker_containers(self):
        """
        Synchronise local Django Container models with remote Docker containers
        """
        ps = get_docker_ps.delay()

        try:
            containers_docker = ps.get(timeout=30)
        except celery.exceptions.TimeoutError as e:
            logging.exception("get_docker_ps timed out (30 seconds)")

        if containers_docker is None:
            # Apparently something is wrong with the remote docker or celery
            # To prevent new task creation by Containers exit beat.
            return

        docker_dict = {x['Id']: x for x in containers_docker}
        docker_set = set(docker_dict.keys())

        # retrieve container from database
        container_set = set(
            Container.objects.values_list('docker_id', flat=True))

        # Work out matching matrix
        #       docker  yes non
        # model x
        # yes           1_1 1_0
        # no            0_1 0_0
        #
        m_1_1 = container_set & docker_set
        m_1_0 = container_set - docker_set
        m_0_1 = docker_set - container_set
        m_0_0 = ((docker_set | container_set) -
                 (docker_set ^ container_set) -
                 (docker_set & container_set)
                 )

        # Update state of all matching containers
        container_match = m_1_1 | m_1_0
        for con_id in container_match:
            snapshot = docker_dict[con_id] if con_id in docker_dict else None
            for c in Container.objects.filter(docker_id=con_id):
                c.update_from_docker_snapshot(snapshot)

        # Call error for mismatch
        container_mismatch = m_0_1 | m_0_0
        for container in container_mismatch:
            self.stderr.write(
                "Docker container {} not found in database!".format(container))
            do_docker_remove.delay(container, force=True)
