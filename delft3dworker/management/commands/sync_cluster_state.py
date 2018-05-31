from celery.result import AsyncResult
import logging
from django.core.management import BaseCommand
from json import loads
from time import sleep

from delft3dcontainermanager.tasks import get_argo_workflows
from delft3dcontainermanager.tasks import do_argo_remove
from delft3dworker.models import Workflow
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
        self._update_workflow_tasks()

        # STEP II : Get current workflows on cluster
        if self._get_latest_workflows_status():

            # STEP III : Update Scenes and their Phases
            # Controls workflow desired states
            self._update_scene_phases()

            # STEP IV : Synchronize Workflow Models with cluster workflows
            self._fix_workflow_state_mismatch()

    def _update_workflow_tasks(self):
        """
        Update Containers with results from finished tasks.
        """
        workflows_with_running_tasks = set(Workflow.objects.exclude(task_uuid__exact=None))

        for workflow in workflows_with_running_tasks:
            workflow.update_task_result()

    def _get_latest_workflows_status(self):
        """
        Synchronise local Django Container models with remote Docker containers
        """

        ps = get_argo_workflows.apply_async(queue='priority')

        # Wait until the task finished successfully
        # or return if waiting too long
        checked = 0
        # TODO Use get or avoid warning
        while not ps.successful():
            sleep(1)

            # if things take too long, revoke the task and return
            checked += 1
            if checked >= 30:
                ps.revoke()
                return False

        # task is succesful, so we're getting the result and create a set
        cluster_workflows_json = ps.result["get_argo_workflows"]
        cluster_workflows = loads(cluster_workflows_json)
        cluster_dict = {wf["metadata"]["name"]: wf for wf in cluster_workflows["items"]}
        cluster_set = set(cluster_dict.keys())

        # retrieve container from database
        database_set = set(Workflow.objects.all().values_list('name', flat=True))

        # Work out matching matrix
        #       argo wf yes no
        # model x
        # yes           1_1 1_0
        # no            0_1 0_0
        #
        m_1_1 = database_set & cluster_set
        m_1_0 = database_set - cluster_set
        m_0_1 = cluster_set - database_set
        m_0_0 = ((cluster_set | database_set) -
                 (cluster_set ^ database_set) -
                 (cluster_set & database_set)
                 )

        # Update state of all matching containers
        workflow_match = m_1_1 | m_1_0
        for wf_name in workflow_match:
            snapshot = cluster_dict[wf_name] if wf_name in cluster_dict else None
            for wf in Workflow.objects.filter(name=wf_name):
                wf.sync_cluster_state(snapshot)

        # Call error for mismatch
        workflow_mismatch = m_0_1 | m_0_0
        for wf in workflow_mismatch:
            print("Mismatch {}".format(wf))
            msg = "Workflow {} not found in database!".format(wf)
            self.stderr.write(msg)
            # do_argo_remove.delay(wf)  # comment out for dev

        return True  # successful

    def _update_scene_phases(self):
        """
        Update Scenes with latest status of their Containers, and possibly
        shift Scene phase
        """

        # ordering is done on start date (first, and id second):
        # if a simulation slot is available, we want simulations to start
        # in order of their date_started
        for scene in Scene.objects.all().order_by('date_started', 'id'):
            scene.update_and_phase_shift()

    def _fix_workflow_state_mismatch(self):

        for workflow in Workflow.objects.all():
            workflow.fix_mismatch_or_log()
