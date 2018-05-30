from __future__ import absolute_import

import copy
import hashlib
import io
import json
import logging
import math
import os
import random
import shutil
import string
import uuid
import yaml
import zipfile

from celery.result import AsyncResult

from django.conf import settings  # noqa
from constance import config as cconfig
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
from django.forms.models import model_to_dict

from model_utils import Choices

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_groups_with_perms
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import remove_perm

# from jsonfield import JSONField
from django.contrib.postgres.fields import JSONField

from delft3dworker.utils import log_progress_parser, version_default, get_version, tz_now

from delft3dcontainermanager.tasks import do_docker_create
from delft3dcontainermanager.tasks import do_docker_remove
from delft3dcontainermanager.tasks import do_docker_start
from delft3dcontainermanager.tasks import do_docker_stop
from delft3dcontainermanager.tasks import get_docker_log

from delft3dcontainermanager.tasks import get_argo_workflows, do_argo_create
from delft3dcontainermanager.tasks import do_argo_remove, get_kube_log


# ################################### VERSION_SVN, SCENARIO, SCENE & CONTAINER


def default_svn_version():
    """Default SVN_Version for new Scenes.
    Also ensure there's always a row in the svn model."""
    if settings.REQUIRE_REVIEW:
        count = Version_SVN.objects.filter(reviewed=True).count()
    else:
        count = Version_SVN.objects.count()

    if count == 0:
        logging.info("Creating default svn trunk model")
        version = Version_SVN(release='trunk', revision=settings.SVN_REV,
                              url=settings.REPOS_URL + '/trunk/', versions={},
                              changelog='default release', reviewed=settings.REQUIRE_REVIEW)
        version.save()
        return version.id
    else:
        return Version_SVN.objects.latest().id


class Version_SVN_Manager(models.Manager):

    def latest(self):
        """Return latest model."""
        if settings.REQUIRE_REVIEW:
            return self.get_queryset().filter(reviewed=True).first()
        else:
            return self.get_queryset().all().first()


class Version_SVN(models.Model):
    """
    Store releases used in the Delft3D-GT svn repository.

    Every scene has a version_svn, if there's a newer (higher id)
    version_svn available, the scene is outdated.

    By comparing svn folders and files (versions field) the specific
    workflow can be determined in the scene.

    The revision and url can be used in the Docker Python env
    """
    objects = Version_SVN_Manager()
    release = models.CharField(
        max_length=256, db_index=True)  # tag/release name
    revision = models.PositiveSmallIntegerField(db_index=True)  # svn_version
    versions = JSONField(default='{}')  # folder revisions
    url = models.URLField(max_length=200)  # repos_url
    changelog = models.CharField(max_length=256)  # release notes
    reviewed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-revision"]
        verbose_name = "SVN version"
        verbose_name_plural = "SVN versions"

    def __unicode__(self):
        return "Release {} at revision {}".format(self.release, self.revision)

    def outdated(self):
        """Return bool if there are newer releases available."""
        return Version_SVN.objects.latest().revision > self.revision

    def compare_outdated(self):
        """Compare folder revisions with latest release."""
        outdated_folders = []

        latest_versions = Version_SVN.objects.latest().versions
        for folder, revision in latest_versions.items():
            if self.versions.setdefault(folder, -1) < revision:
                outdated_folders.append(folder)

        return outdated_folders


class Scenario(models.Model):

    """
    Scenario model
    """

    name = models.CharField(max_length=256)

    template = models.ForeignKey(
        'Template', blank=True, null=True, on_delete=models.CASCADE)

    scenes_parameters = JSONField(blank=True, default={})
    parameters = JSONField(blank=True, default={})

    owner = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    state = models.CharField(max_length=64, default="CREATED")
    progress = models.IntegerField(default=0)  # 0-100

    # PROPERTY METHODS

    class Meta:
        permissions = (
            ('view_scenario', 'View Scenario'),
        )

    def load_settings(self, settings):
        self.parameters = settings
        self.scenes_parameters = [{}]

        for key, value in self.parameters.items():
            self._parse_setting(key, value)

        self.save()

    def createscenes(self, user):
        for i, sceneparameters in enumerate(self.scenes_parameters):
            # Create hash
            m = hashlib.sha256()
            m.update(str(sceneparameters))
            phash = m.hexdigest()

            # Check if hash already exists
            scenes = Scene.objects.filter(parameters_hash=phash)
            clones = get_objects_for_user(
                user, "view_scene", scenes, accept_global_perms=False)

            # If so, add scenario to scene
            if len(clones) > 0:
                scene = clones[0]  # cannot have more than one scene
                scene.scenario.add(self)

            # Scene input is unique
            else:
                scene = Scene(
                    name="{}: Run {}".format(self.name, i + 1),
                    owner=self.owner,
                    parameters=sceneparameters,
                    shared="p",  # private
                    parameters_hash=phash,
                    info=self.template.info
                )
                scene.save()
                scene.scenario.add(self)

                assign_perm('add_scene', self.owner, scene)
                assign_perm('change_scene', self.owner, scene)
                assign_perm('delete_scene', self.owner, scene)
                assign_perm('view_scene', self.owner, scene)

        self.save()

    # CONTROL METHODS

    def start(self, user):
        for scene in self.scene_set.all():
            if user.has_perm('delft3dworker.change_scene', scene):
                scene.start()
        return "started"

    def redo(self, user):
        for scene in self.scene_set.all():
            if user.has_perm('delft3dworker.change_scene', scene):
                scene.redo()
        return "redoing"

    def abort(self, user):
        for scene in self.scene_set.all():
            if user.has_perm('delft3dworker.change_scene', scene):
                scene.abort()
        self.state = "ABORTED"
        return self.state

    # CRUD METHODS

    def delete(self, user, *args, **kwargs):
        for scene in self.scene_set.all():
            if len(scene.scenario.all()) == 1 and user.has_perm(
                    'delft3dworker.delete_scene', scene):
                scene.delete()
        super(Scenario, self).delete(*args, **kwargs)

    # SHARING

    def publish_company(self, user):
        # Loop over all scenes and publish where possible
        for scene in self.scene_set.all():
            if user.has_perm('delft3dworker.add_scene', scene):
                scene.publish_company(user)

    def publish_world(self, user):
        # Loop over all scenes and publish where possible
        for scene in self.scene_set.all():
            if user.has_perm('delft3dworker.add_scene', scene):
                scene.publish_world(user)

    # INTERNALS

    # TODO Workflow update this
    def _update_state_and_save(self):

        count = self.scene_set.all().count()
        self.state = 'inactive'

        if count > 0:
            progress = 0
            for scene in self.scene_set.all():
                progress = progress + scene.progress
                # TODO Fix phases here
                if scene.phase != 6:
                    self.state = 'active'

            self.progress = progress / count
            self.save()

        return self.state

    def _parse_setting(self, key, setting):
        if not ('values' in setting):
            return

        values = setting['values']

        if key == "scenarioname":
            self.name = values
            return

        # If values is a list, multiply scenes
        if isinstance(values, list):
            logging.info("Detected multiple values at {}".format(key))

            # Current scenes times number of new values
            # 3 original runs (1 2 3), this settings adds two (a b) thus we now
            # have 6 scenes ( 1 1 2 2 3 3).
            self.scenes_parameters = [
                copy.copy(p) for p in
                self.scenes_parameters for _ in range(len(values))
            ]

            i = 0
            for scene in self.scenes_parameters:
                s = dict(setting)  # by using dict, we prevent an alias
                # Using modulo we can assign a b in the correct
                # way (1a 1b 2a 2b 3a 3b), because at index 2 (the first 2)
                # modulo gives 0 which is again the first value (a)
                # Rename key in settings
                s['value'] = values[i % len(values)]
                # delete keys named 'values'
                s.pop('values')
                scene[key] = s
                i += 1

        # Set keys not yet occuring in scenes
        else:
            for scene in self.scenes_parameters:
                if key not in scene:
                    scene[key] = setting

    def __unicode__(self):
        return self.name


class Scene(models.Model):

    """
    Scene model
    """

    name = models.CharField(max_length=256)

    suid = models.UUIDField(default=uuid.uuid4, editable=False)

    scenario = models.ManyToManyField(Scenario, blank=True)

    date_created = models.DateTimeField(default=tz_now, blank=True)
    date_started = models.DateTimeField(blank=True, null=True)

    fileurl = models.CharField(max_length=256)
    info = JSONField(blank=True, default={})
    parameters = JSONField(blank=True, default={})  # {"dt":20}
    state = models.CharField(max_length=256, default="CREATED")
    progress = models.IntegerField(default=0)
    task_id = models.CharField(max_length=256, blank=True)

    # TODO: use FilePath Field
    workingdir = models.CharField(max_length=256)
    parameters_hash = models.CharField(max_length=64, blank=True)

    shared_choices = [('p', 'private'), ('c', 'company'), ('w', 'world')]
    shared = models.CharField(max_length=1, choices=shared_choices)
    owner = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    # TODO Make this into entrypoints? Otherwise delete.
    entrypoints = Choices(
        (0, 'main', 'main workflow'),
        # (1, 'redo_proc', 'redo processing workflow'),
        # (2, 'redo_postproc', 'redo postprocessing workflow'),
        # (3, 'redo_proc_postproc', 'redo processing and postprocessing workflow')
    )

    entrypoint = models.PositiveSmallIntegerField(
        default=entrypoints.main, choices=entrypoints)

    phases = Choices(
        # Create workflow models
        (0, 'new', 'New'),

        # User input wait phase
        (6, 'idle', 'Idle: waiting for user input'),

        # Workflow phases
        (11, 'sim_start', 'Starting workflow'),
        (12, 'sim_run', 'Running workflow'),
        (13, 'sim_fin', 'Removing workflow'),

        # Other phases
        (500, 'fin', 'Finished'),
        (501, 'fail', 'Failed'),
    )

    phase = models.PositiveSmallIntegerField(default=phases.new, choices=phases)
    version = models.ForeignKey(
        Version_SVN, default=default_svn_version, on_delete=models.CASCADE)

    # PROPERTY METHODS

    class Meta:
        permissions = (
            ('view_scene', 'View Scene'),
        )

    def versions(self):
        version_dict = model_to_dict(self.version)
        version_dict['delft3d_version'] = settings.DELFT3D_VERSION
        return version_dict

    def is_outdated(self):
        return self.version.outdated()

    def outdated_workflow(self):
        if self.is_outdated():
            outdated_folders = self.version.compare_outdated()

            if ('postprocess' in outdated_folders or 'export' in outdated_folders) and ('process' in outdated_folders or 'visualisation' in outdated_folders):
                return self.workflows.redo_proc_postproc

            elif ('postprocess' in outdated_folders or 'export' in outdated_folders):
                return self.workflows.redo_postproc

            elif ('process' in outdated_folders or 'visualisation' in outdated_folders):
                return self.workflows.redo_proc

            # Default model is trunk with a revision number, but without any folder
            # revisions
            elif len(outdated_folders) == 0:
                return self.workflows.redo_proc_postproc

            else:
                logging.error("Unable to resolve workflow for outdated scene. Folders: {}".format(
                    outdated_folders))
                return None
        else:
            return None

    def outdated_changelog(self):
        if self.is_outdated():
            return Version_SVN.objects.latest().changelog
        else:
            return ""

    # UI CONTROL METHODS

    def reset(self):
        return self.redo()

    def start(self):
        # only allow a start when Scene is 'Idle'
        if self.phase == self.phases.idle:
            self.shift_to_phase(self.phases.sim_start)   # shift to Queued
            self.date_started = tz_now()
            self.save()

        return {"task_id": None, "scene_id": None}

    def redo(self):
        # only allow a redo when Scene is 'Finished'
        if self.phase == self.phases.fin:
            self.date_started = tz_now()
            self.shift_to_phase(self.phases.sim_start)
            self.save()

        return {"task_id": None, "scene_id": None}

    def abort(self):
        # Stop simulation
        if self.phase >= self.phases.sim_start and self.phase <= self.phases.sim_fin:
            self.shift_to_phase(self.phases.sim_fin)   # stop Simulation

        # Abort queue
        if self.phase == self.phases.queued:
            self.shift_to_phase(self.phases.idle)  # get out of queue

        return {
            "task_id": None,
            "state": None,
            "info": None
        }

    def export(self, zipfile, options):
        # Add files here.
        # If you run out of memory you have 2 options:
        # - stream
        # - zip in a subprocess shell with zip
        # - zip to temporary file

        # TODO Export based on export in Template

        available_options = self.Template.export_options
        files_added = False

        # for root, dirs, files in os.walk(self.workingdir):
        #     for f in files:
        #         name, ext = os.path.splitext(f)

        #         # Available options and extensions logic
        #         add = False

        #         if add:
        #             files_added = True
        #             abs_path = os.path.join(root, f)
        #             rel_path = os.path.join(slugify(self.name),
        #                                     os.path.relpath(abs_path, self.workingdir))
        #             zipfile.write(abs_path, rel_path)

        return files_added

    # CRUD METHODS

    def save(self, *args, **kwargs):

        # On first save
        if self.pk is None:
            self.workingdir = os.path.join(
                settings.WORKER_FILEDIR,
                str(self.suid),
                ''
            )
            self.fileurl = os.path.join(
                settings.WORKER_FILEURL, str(self.suid), '')

        super(Scene, self).save(*args, **kwargs)

    def delete(self, deletefiles=True, *args, **kwargs):
        self.abort()
        if deletefiles:
            self._delete_datafolder()
        super(Scene, self).delete(*args, **kwargs)

    # SHARING

    def publish_company(self, user):
        if self.shared != "p":
            return
        if self.phase != self.phases.fin:
            return

        remove_perm('change_scene', user, self)  # revoke PUT rights
        remove_perm('delete_scene', user, self)  # revoke POST rights

        # Set permissions for groups
        groups = [group for group in user.groups.all() if (
            "access" in group.name and "world" not in group.name
        )]
        for group in groups:
            assign_perm('view_scene', group, self)

        # update scene
        self.shared = "c"
        self.save()

    def publish_world(self, user):
        if self.phase != self.phases.fin:
            return

        remove_perm('add_scene', user, self)  # revoke POST rights
        remove_perm('change_scene', user, self)  # revoke PUT rights
        remove_perm('delete_scene', user, self)  # revoke DELETE rights

        # Set permissions for groups
        for group in get_groups_with_perms(self):
            remove_perm('view_scene', group, self)
        world = Group.objects.get(name="access:world")
        assign_perm('view_scene', world, self)

        # update scene
        self.shared = "w"
        self.save()

    # HEARTBEAT UPDATE AND SAVE

    def update_and_phase_shift(self):

        # Create Workflow model and shift to idle
        if self.phase == self.phases.new:

            if not hasattr(self, 'workflow'):
                workflow = Workflow.objects.create(
                    scene=self,
                    name="{}-{}".format(self.scenario.first().template.shortname, self.suid),
                )
                workflow.save()

            self.shift_to_phase(self.phases.idle)

            return

        # User started a scene. Create Workflow and shift if it's running.
        elif self.phase == self.phases.sim_start:

            self.workflow.set_desired_state('running')
            if (self.workflow.cluster_state == 'running'):
                self.shift_to_phase(self.phases.sim_run)

            elif (self.workflow.cluster_state in Workflow.FINISHED):
                self.shift_to_phase(self.phases.sim_fin)

            return

        # While running, scan for new pictures
        elif self.phase == self.phases.sim_run:
            self._local_scan_process()  # update images and logfile
            self._parse_postprocessing()
            self.progress = self.workflow.progress
            self.save()

            # If workflow is finished, shift to finished
            if (self.workflow.cluster_state == 'finished'):
                self.shift_to_phase(self.phases.sim_fin)

            # If workflow disappeared, shift back
            elif (self.workflow.cluster_state == 'non-existent'):
                logging.error("Lost sim/process container!")
                self.shift_to_phase(self.phases.sim_start)

            return

        # Delete workflow in cluster
        elif self.phase == self.phases.sim_fin:

            self.workflow.set_desired_state('non-existent')

            if (self.workflow.cluster_state != 'non-existent'):
                self.progress = self.workflow.progress
                self.save()
            else:
                self.shift_to_phase(self.phases.fin)

            return

        else:
            return

    def shift_to_phase(self, new_phase):
        self.phase = new_phase
        self.save()

    # INTERNALS

    # TODO Remove method and update code calls
    def _delete_datafolder(self):
        # delete directory for scene
        if os.path.exists(self.workingdir):
            try:
                shutil.rmtree(self.workingdir)
            except:
                # Files written by root can't be deleted by django
                logging.error("Failed to delete working directory")

    def _update_state_and_save(self):

        # TODO: write _update_state_and_save method
        return self.state

    def _local_scan_process(self):
        # TODO: get the info about what to scan from
        # the template in the scenario instead of hardcoding
        for root, dirs, files in os.walk(
            os.path.join(self.workingdir, 'process')
        ):
            for f in sorted(files):
                name, ext = os.path.splitext(f)
                if ext in ('.png', '.jpg', '.gif'):
                    # TODO use get to check image list and
                    # make this code less deep in if/for statements
                    if ("delta_fringe" in name and f not in self.info[
                            "delta_fringe_images"]["images"]):
                        self.info["delta_fringe_images"][
                            "images"].append(f)
                    elif ("channel_network" in name and f not in self.info[
                            "channel_network_images"]["images"]):
                        self.info["channel_network_images"][
                            "images"].append(f)
                    elif ("sediment_fraction" in name and
                          f not in self.info[
                            "sediment_fraction_images"]["images"]):
                        self.info["sediment_fraction_images"][
                            "images"].append(f)
                    elif ("subenvironment" in name and
                          f not in self.info[
                            "subenvironment_images"]["images"]):
                        self.info["subenvironment_images"][
                            "images"].append(f)
                    else:
                        # Other images ?
                        pass

        # If no log path is yet known, set log
        # so don't update this everytime
        if self.info["logfile"]["file"] == "":
            for root, dirs, files in os.walk(
                os.path.join(self.workingdir, 'simulation')
            ):
                for f in files:
                    if f == 'delft3d.log':
                        # No log is generated at the moment
                        self.info["logfile"]["file"] = f
                        break
        self.save()

    # Run this after post processing
    # TODO This won't work with workflows
    def _parse_postprocessing(self):
        outputfn = os.path.join(self.workingdir, 'postprocess', 'output.json')
        if os.path.exists(outputfn):
            with open(outputfn) as f:
                try:
                    output_dict = json.load(f)
                except:
                    logging.error("Error parsing postprocessing output.json")
            self.info["postprocess_output"].update(output_dict)
        else:
            logging.error("Couldn't find postprocessing output.json")
        self.save()

    def __unicode__(self):
        return self.name


class Container(models.Model):
    """
    Container Model
    This model is used to manage docker containers from the Django environment.
    When a Scene creates Container models, it uses these containers to define
    which containers it requires, and in which states these containers are
    desired to be.
    """

    scene = models.ForeignKey(Scene, on_delete=models.CASCADE)

    task_uuid = models.UUIDField(
        default=None, blank=True, null=True)
    task_starttime = models.DateTimeField(default=tz_now, blank=True)

    # delft3dgtmain.provisionedsettings
    CONTAINER_TYPE_CHOICES = (
        ('preprocess', 'preprocess'),
        ('delft3d', 'delft3d'),
        ('process', 'process'),
        ('postprocess', 'postprocess'),
        ('export', 'export'),
        ('sync_cleanup', 'sync_cleanup'),
        ('sync_rerun', 'sync_rerun'),
    )

    container_type = models.CharField(
        max_length=16, choices=CONTAINER_TYPE_CHOICES, default='preprocess')

    # https://docs.docker.com/engine/reference/commandline/ps/
    CONTAINER_STATE_CHOICES = (
        ('non-existent', 'non-existent'),
        ('created', 'created'),
        ('restarting', 'restarting'),
        ('running', 'running'),
        ('paused', 'paused'),
        ('exited', 'exited'),
        ('dead', 'dead'),
        ('unknown', 'unknown'),
    )

    desired_state = models.CharField(
        max_length=16, choices=CONTAINER_STATE_CHOICES, default='non-existent')

    docker_state = models.CharField(
        max_length=16, choices=CONTAINER_STATE_CHOICES, default='non-existent')

    # docker container ids are sha256 hashes
    docker_id = models.CharField(
        max_length=64, blank=True, default='', db_index=True)

    container_starttime = models.DateTimeField(default=tz_now, blank=True)
    container_stoptime = models.DateTimeField(default=tz_now, blank=True)
    container_exitcode = models.PositiveSmallIntegerField(default=0)
    container_progress = models.PositiveSmallIntegerField(default=0)

    docker_log = models.TextField(blank=True, default='')
    container_log = models.TextField(blank=True, default='')

    # CONTROL METHODS

    def set_desired_state(self, desired_state):
        self.desired_state = desired_state
        self.save()

    # HEARTBEAT METHODS

    def update_task_result(self):
        """
        Get the result from the last task it executed, given that there is a
        result. If the task is not ready, don't do anything.
        """
        if self.task_uuid is None:
            return

        result = AsyncResult(id=str(self.task_uuid))
        time_passed = now() - self.task_starttime
        if result.ready():

            if result.successful():
                docker_id, docker_log = result.result
                # only write the id if the result is as expected
                if docker_id is not None and (isinstance(docker_id, str) or
                                              isinstance(docker_id, unicode)):
                    self.docker_id = docker_id
                else:
                    logging.warn(
                        "Task of Container [{}] returned an unexpected "
                        "docker_id: {}".format(self, docker_id))

                # only write the log if the result is as expected and there is
                # an actual log
                if docker_log is not None and isinstance(
                        docker_log, unicode) and docker_log != '':
                    self.docker_log = docker_log
                    progress = log_progress_parser(self.docker_log,
                                                   self.container_type)
                    if progress is not None:
                        self.container_progress = math.ceil(progress)
                else:
                    logging.warn("Can't parse docker log of {}".
                                 format(self.container_type))

            else:
                error = result.result
                logging.warn(
                    "Task of Container [{}] resulted in {}: {}".
                    format(self, result.state, error))

            self.task_uuid = None
            self.save()

        # Forget task after 5 minutes
        elif time_passed.total_seconds() > settings.TASK_EXPIRE_TIME:
            logging.warn(
                "Celery task expired after {} seconds".format(
                    time_passed.total_seconds()))
            result.revoke()
            self.task_uuid = None
            self.save()

        else:
            logging.warn("Celery task of {} is still {}.".format(self,
                                                                 result.state))

    def update_from_docker_snapshot(self, snapshot):
        """
        Update the Container based on a given snapshot of a docker container
        which was retrieved with docker-py's client.containers(all=True)
        (equivalent to 'docker ps').

        Parameter snapshot can be either dictionary or None.
        If None: docker container does not exist
        If dictionary:
        {...,
            "State": {
                "Dead": false,
                "Error": "",
                "ExitCode": 0,
                "FinishedAt": "2016-08-30T10:33:41.159456168Z",
                "OOMKilled": false,
                "Paused": false,
                "Pid": 0,
                "Restarting": false,
                "Running": false,
                "StartedAt": "2016-08-30T10:32:31.415322502Z",
                "Status": "exited"
            },
        ...
        }
        """

        if snapshot is None:
            self.docker_state = 'non-existent'
            self.docker_id = ''

        elif isinstance(snapshot, dict) and \
                ('State' in snapshot) and ('Status' in snapshot['State']):

            choices = [choice[1] for choice in self.CONTAINER_STATE_CHOICES]
            if snapshot['State']['Status'] in choices:
                self.docker_state = snapshot['State']['Status']

            else:
                logging.error(
                    'received unknown docker Status: {}'.format(
                        snapshot['State']['Status']
                    )
                )
                self.docker_state = 'unknown'

            if 'StartedAt' in snapshot['State'] and \
                    'FinishedAt' in snapshot['State']:
                self.container_starttime = snapshot['State']['StartedAt']
                self.container_stoptime = snapshot['State']['FinishedAt']

            if 'ExitCode' in snapshot['State']:
                self.container_exitcode = snapshot['State']['ExitCode']

        else:
            logging.error('received unknown snapshot: {}'.format(snapshot))
            self.docker_state = 'unknown'

        self.save()

    def fix_mismatch_or_log(self):
        """
        Given that the container has no pending tasks, Compare this state to
        the its desired_state, which is defined by the Scene to which this
        Container belongs. If (for any reason) the docker_state is different
        from the desired_state, act: start a task to get both states matched.

        At the end, if still no task, request a log update.
        """
        self._fix_state_mismatch()

        self._update_log()

    # INTERNALS

    def _fix_state_mismatch(self):
        """
        If the docker_state differs from the desired_state, and Container is
        not waiting for a task result, execute a task to fix this mismatch.
        """

        # return if container still has an active task
        if self.task_uuid is not None:
            return

        # return if the states match
        if self.desired_state == self.docker_state:
            return

        # apparently there is something to do, so let's act:

        if self.desired_state == 'created':
            self._create_container()

        elif self.desired_state == 'running':
            self._start_container()

        elif self.desired_state == 'exited':
            self._stop_container()

        elif self.desired_state == 'non-existent':
            self._remove_container()

    def _create_container(self):
        if self.docker_state != 'non-existent':
            return  # container is already created

        workingdir = self.scene.workingdir
        simdir = os.path.join(workingdir, 'simulation')
        predir = os.path.join(workingdir, 'preprocess')
        prodir = os.path.join(workingdir, 'process')
        posdir = os.path.join(workingdir, 'postprocess')
        expdir = os.path.join(workingdir, 'export')
        syndir = workingdir

        # Specific settings for each container type
        # TODO It would be more elegant to put these
        # hard-coded settings in a separate file.
        #
        # Also have a template that comes from
        # provisioning, to match the needed environment variables

        # Random string in order to avoid naming conflicts.
        # We want new containers when old ones fail in Docker Swarm
        # but Docker Swarm still recognizes the old names.
        random_postfix = ''.join(random.SystemRandom().choice(
            string.ascii_uppercase + string.digits) for _ in range(5))

        kwargs = {
            'delft3d': {'image': settings.DELFT3D_IMAGE_NAME,
                        'volumes': ['{0}:/data'.format(simdir)],
                        'memory_limit': '3g',  # 75% of t2.medium
                        'environment': {"uuid": str(self.scene.suid),
                                        "folder": simdir},
                        'name': "{}-{}-{}".format(self.container_type,
                                                  str(self.scene.suid),
                                                  random_postfix),
                        'folders': [simdir],
                        'command': ""},

            'export': {'image': settings.EXPORT_IMAGE_NAME,
                       'volumes': [
                           '{0}:/data/output:z'.format(expdir),
                           '{0}:/data/input:ro'.format(simdir),
                           '{0}:/data/input_postproc:ro'.format(posdir)],
                       'memory_limit': '2000m',
                       'environment': {"uuid": str(self.scene.suid),
                                       "folder": expdir},
                       'name': "{}-{}-{}".format(self.container_type,
                                                 str(self.scene.suid),
                                                 random_postfix),
                       'folders': [expdir,
                                   simdir],
                       'command': "/data/run.sh /data/svn/scripts/"
                       "export/export2grdecl.py",
                       },

            'postprocess': {'image': settings.POSTPROCESS_IMAGE_NAME,
                            'volumes': [
                                '{0}:/data/output:z'.format(posdir),
                                '{0}:/data/input:ro'.format(simdir)],
                            'memory_limit': '3000m',
                            'environment': {"uuid": str(self.scene.suid),
                                            "folder": posdir},
                            'name': "{}-{}-{}".format(self.container_type,
                                                      str(self.scene.suid),
                                                      random_postfix),
                            'folders': [simdir,
                                        posdir],
                            'command': " ".join([
                                "/data/run.sh",
                                "/data/svn/scripts/wrapper/postprocess.py"
                            ])
                            },

            'preprocess': {'image': settings.PREPROCESS_IMAGE_NAME,
                           'volumes': [
                               '{0}:/data/output:z'.format(simdir),
                               '{0}:/data/input:ro'.format(predir)],
                           'memory_limit': '200m',
                           'environment': {"uuid": str(self.scene.suid),
                                           "folder": simdir},
                           'name': "{}-{}-{}".format(self.container_type,
                                                     str(self.scene.suid),
                                                     random_postfix),
                           'folders': [predir,
                                       simdir],
                           'command': "/data/run.sh /data/svn/scripts/"
                           "preprocess/preprocess.py"
                           },

            'sync_cleanup': {'image': settings.SYNC_CLEANUP_IMAGE_NAME,
                             'volumes': [
                                 '{0}:/data/input:z'.format(syndir)],
                             'memory_limit': '500m',
                             'environment': {"uuid": str(self.scene.suid),
                                             "folder": syndir},
                             'name': "{}-{}-{}".format(self.container_type,
                                                       str(self.scene.suid),
                                                       random_postfix),
                             'folders': [],  # sync doesn't need new folders
                             'command': "/data/run.sh cleanup"
                             },

            'sync_rerun': {'image': settings.SYNC_CLEANUP_IMAGE_NAME,
                           'volumes': [
                               '{0}:/data/output:z'.format(syndir)],
                           'memory_limit': '500m',
                           'environment': {"uuid": str(self.scene.suid),
                                           "folder": syndir},
                           'name': "{}-{}-{}".format(self.container_type,
                                                     str(self.scene.suid),
                                                     random_postfix),
                           'folders': [simdir],
                           'command': "/data/run.sh rerun"
                           },

            'process': {'image': settings.PROCESS_IMAGE_NAME,
                        'volumes': [
                            '{0}:/data/input:ro'.format(simdir),
                            '{0}:/data/output:z'.format(prodir)
                        ],
                        'memory_limit': '3000m',
                        'environment': {"uuid": str(self.scene.suid),
                                        "folder": prodir},
                        'name': "{}-{}-{}".format(self.container_type,
                                                  str(self.scene.suid),
                                                  random_postfix),
                        'folders': [prodir,
                                    simdir],
                        'command': ' '.join([
                            "/data/run.sh ",
                            "/data/svn/scripts/wrapper/process.py"
                        ])
                        },
        }

        # Set SVN_REV and REPOS_URL a.o.
        version = model_to_dict(self.scene.version)
        kwargs[self.container_type]['environment'].update({'REPOS_URL': version['url'],
                                                           'SVN_REV': version['revision']})

        parameters = self.scene.parameters
        label = {"type": self.container_type}

        result = do_docker_create.apply_async(
            args=(label, parameters),
            kwargs=kwargs[self.container_type],
            expires=settings.TASK_EXPIRE_TIME
        )

        self.task_starttime = now()
        self.container_log += str(self.task_starttime) + \
            "Container was created \n"

        self.task_uuid = result.id
        self.save()

        # Return name because of random part at the end
        return kwargs[self.container_type]['name']

    def _start_container(self):
        # a container can only be started if it is in 'created' or 'exited'
        # state, any other state we will not allow a start
        if self.docker_state != 'created' and self.docker_state != 'exited':
            logging.info('Trying to start a container in "{}" state: ignoring '
                         'command.'.format(self.docker_state))
            return  # container is not ready for start

        result = do_docker_start.apply_async(args=(self.docker_id,),
                                             expires=settings.TASK_EXPIRE_TIME)
        self.task_starttime = now()
        self.container_log += str(self.task_starttime) + \
            "Container was started \n"

        self.task_uuid = result.id
        self.save()

    def _stop_container(self):
        # a container can only be started if it is in 'running' state, any
        # state we will not allow a stop
        if self.docker_state != 'running':
            logging.info('Trying to stop a container in "{}" state: ignoring '
                         'command.'.format(self.docker_state))
            return  # container is not running, so it can't be stopped

        # I just discovered how to make myself unstoppable: don't move.

        result = do_docker_stop.apply_async(args=(self.docker_id,),
                                            expires=settings.TASK_EXPIRE_TIME)
        self.task_starttime = now()
        self.container_log += str(self.task_starttime) + \
            "Container was stopped \n"

        self.task_uuid = result.id
        self.save()

    def _remove_container(self):
        # a container can only be removed if it is in 'created' or 'exited'
        # state, any other state we will not allow a remove
        if self.docker_state != 'created' and self.docker_state != 'exited':
            logging.info('Trying to remove a container in "{}" state: ignoring'
                         ' command.'.format(self.docker_state))
            return  # container not ready for delete

        result = do_docker_remove.apply_async(
            args=(self.docker_id,),
            expires=settings.TASK_EXPIRE_TIME
        )

        self.task_starttime = now()
        self.container_log += str(self.task_starttime) + \
            "Container was removed \n"

        self.task_uuid = result.id
        self.save()

    def _update_log(self):
        # return if container still has an active task
        if self.task_uuid is not None:
            return

        if self.docker_state != 'running':
            return  # the container is done, no logging needed

        result = get_docker_log.apply_async(args=(self.docker_id,),
                                            expires=settings.TASK_EXPIRE_TIME)
        self.task_starttime = now()
        self.task_uuid = result.id
        self.save()

    def __unicode__(self):
        return "{}({}):{}".format(
            self.container_type, self.docker_state, self.docker_id)


# ################################### SEARCHFORM & TEMPLATE

class SearchForm(models.Model):

    """
    SearchForm model:
    This model is used to make a search form similar to the Template model.
    The idea was to provide a json to the front-end similar to how we deliver
    the Templates: via the API.
    Possible improvements: Because we only have one SearchForm, we could
    implement a 'view' on all Templates, which automatically generates the
    json at each request.
    """

    name = models.CharField(max_length=256)
    templates = JSONField(default=[])
    sections = JSONField(default=[])

    def update(self):
        self.templates = "[]"
        self.sections = "[]"
        for template in Template.objects.all():
            self._update_templates(template.name, template.id)
            self._update_sections(template.sections)
        return

    def _update_templates(self, tmpl_name, tmpl_id):
        self.templates.append({
            'name': tmpl_name,
            'id': tmpl_id,
        })

    def _update_sections(self, tmpl_sections):

        # for each section
        for tmpl_section in tmpl_sections:

            # find matching (i.e. name && type equal) sections
            # in this search form
            matching_sections = [section for section in self.sections if (
                section["name"] == tmpl_section["name"]
            )]

            # add or update
            if not matching_sections:

                # remove non-required fields from variables
                for variable in tmpl_section["variables"]:
                    try:
                        del variable["default"]
                    except KeyError:
                        pass  # if no default is in the dict, no worries
                    try:
                        del variable["validators"]["required"]
                    except KeyError:
                        pass  # if no required is in the dict, no worries

                self.sections.append(tmpl_section)

            else:

                srch_section = matching_sections[0]

                # for each variable
                for tmpl_variable in tmpl_section["variables"]:

                    # find matching (i.e. name equal) sections
                    # in this search form
                    matching_variables = [
                        variable for variable in srch_section["variables"] if (
                            variable["name"] == tmpl_variable["name"]
                        )
                    ]

                    # add or update
                    if not matching_variables:

                        # remove non-required fields from variables
                        try:
                            del tmpl_variable["default"]
                        except KeyError:
                            pass  # if no default is in the dict, no worries
                        try:
                            del tmpl_variable["validators"]["required"]
                        except KeyError:
                            pass  # if no required is in the dict, no worries
                        srch_section["variables"].append(tmpl_variable)

                    else:

                        srch_variable = matching_variables[0]

                        # only update min and max validators if numeric
                        if (
                            srch_variable["type"] == "numeric" and
                            tmpl_variable["type"] == "numeric"
                        ):

                            tmpl_validators = tmpl_variable["validators"]
                            srch_validators = srch_variable["validators"]

                            if (
                                float(tmpl_validators["min"]) < float(
                                    srch_validators["min"])
                            ):
                                srch_validators["min"] = tmpl_validators["min"]

                            if (
                                float(tmpl_validators["max"]) > float(
                                    srch_validators["max"])
                            ):
                                srch_validators["max"] = tmpl_validators["max"]

        self.save()
        return

    def __unicode__(self):
        return self.name


class Template(models.Model):

    """
    Template model
    """

    name = models.CharField(max_length=256)
    shortname = models.CharField(max_length=256, default="gt")
    meta = JSONField(blank=True, default={})
    # TODO Base this on template row.
    info = JSONField(blank=True, default={
        "delta_fringe_images": {
            "images": [],
            "location": "process/"
        },
        "channel_network_images": {
            "images": [],
            "location": "process/"
        },
        "sediment_fraction_images": {
            "images": [],
            "location": "process/"
        },
        "subenvironment_images": {
            "images": [],
            "location": "postprocess/"
        },
        "logfile": {
            "file": "",
            "location": "simulation/"
        },
        "procruns": 0,
        "postprocess_output": {},
    })
    sections = JSONField(blank=True, default={})
    visualisation = JSONField(blank=True, default={})
    export_options = JSONField(blank=True, default={})
    yaml_template = models.FileField(upload_to='workflow_templates/', default="")

    # The following method is disabled as it adds to much garbage
    # to the MAIN search template
    # TODO: implement proper search template which uses REST list_views

    # def save(self, *args, **kwargs):
    #     returnval = super(Template, self).save(*args, **kwargs)

    #     # update the MAIN search form after any template save
    #     searchform, created = SearchForm.objects.get_or_create(name="MAIN")
    #     searchform.update()

    #     return returnval

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):

        # On first save set a shortname
        if self.pk is None:
            self.shortname = self.name.replace(" ", "-").lower()
        super(Template, self).save(*args, **kwargs)

    class Meta:
        permissions = (
            ('view_template', 'View Template'),
        )


class Workflow(models.Model):
    """Argo Workflow Instance."""
    # name exists of name of linked Template and the scene suid
    name = models.CharField(max_length=256, unique=True)
    scene = models.OneToOneField(Scene, on_delete=models.CASCADE)
    starttime = models.DateTimeField(default=tz_now, blank=True)
    yaml = models.FileField(upload_to='workflows/', default="")

    # Celery connected task
    task_uuid = models.UUIDField(
        default=None, blank=True, null=True)
    task_starttime = models.DateTimeField(default=tz_now, blank=True)

    # State management
    WORKFLOW_STATE_CHOICES = (
        ('non-existent', 'Non-existent'),  # on creation
        ('pending', 'Pending'),  # argo ""
        ('unknown', 'Unknown'),  # argo ""
        ('running', 'Running'),
        ('paused', 'Running (Suspended)'),
        ('succeeded', 'Succeeded'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
        ('error', 'Error'),
    )
    FINISHED = ['succeeded', 'failed', 'error', 'skipped']
    desired_state = models.CharField(
        max_length=16, choices=WORKFLOW_STATE_CHOICES, default='non-existent')
    cluster_state = models.CharField(
        max_length=16, choices=WORKFLOW_STATE_CHOICES, default='non-existent')

    # Logging and progress
    progress = models.PositiveSmallIntegerField(default=0)
    cluster_log = models.TextField(blank=True, default="")
    action_log = models.TextField(blank=True, default="")

    # HEARTBEAT METHODS
    def update_task_result(self):
        """
        Get the result from the last task it executed, given that there is a
        result. If the task is not ready, don't do anything.
        """
        if self.task_uuid is None:
            return

        result = AsyncResult(id=str(self.task_uuid))
        print(dir(result))
        time_passed = now() - self.task_starttime
        if result.ready():

            if result.successful():
                # Log parsing
                if "get_kube_log" in result.result:
                    log = result.result["get_kube_log"]

                    cluster_log += "---------\n"
                    cluster_log += log

                    progress = log_progress_parser(log, "delft3d")
                    if progress is not None:
                        self.container_progress = math.ceil(progress)

                else:
                    _ = result.result
                
            else:
                error = result.result
                logging.warn(
                    "Task of Container [{}] resulted in {}: {}".
                    format(self, result.state, error))

            self.task_uuid = None
            self.save()

        # Forget task after expire_time
        elif time_passed.total_seconds() > settings.TASK_EXPIRE_TIME:
            logging.warn(
                "Celery task expired after {} seconds".format(
                    time_passed.total_seconds()))
            result.revoke()
            self.task_uuid = None
            self.save()

        else:
            logging.warn("Celery task of {} is still {}.".format(self,
                                                                 result.state))

    def sync_cluster_state(self, latest_cluster_state):
        if latest_cluster_state is None:
            self.cluster_state = "non-existent"
        else:
            state = latest_cluster_state["metadata"]["labels"]["workflows.argoproj.io/phase"]
            print("Syncing state {}".format(state))
            self.cluster_state = state.lower()
        self.save()

    def fix_mismatch_or_log(self):
        """
        Given that the workflow has no pending tasks, Compare this state to
        the its desired_state, which is defined by the Scene to which this
        Workflow belongs. If (for any reason) the cluster_state is different
        from the desired_state, act: start a task to get both states matched.

        At the end, if still no task, request a log update.
        """
        self.fix_mismatch()
        self.update_log()

    def fix_mismatch(self):
        # return if container still has an active task
        if self.task_uuid is not None:
            return

        # return if the states match
        if self.desired_state == self.cluster_state:
            return

        # apparently there is something to do, so let's act:
        if self.desired_state == 'running':
            self.create_workflow()

        if self.desired_state == 'non-existent':
            self.remove_workflow()

    # INTERNALS
    def set_desired_state(self, desired_state):
        self.desired_state = desired_state
        self.save()

    # CELERY TASK CALLS
    def create_workflow(self):
        # Catch creating already existing workflows
        if self.cluster_state != 'non-existent':
            logging.warning("Can't create already existing workflow.")
            return

        # Open and edit workflow Template
        template_model = self.scene.scenario.first().template
        with open(template_model.yaml_template.path) as f:
            template = yaml.load(f)
        template["metadata"] = {"name": "{}".format(self.name)}
        template["spec"]["arguments"]["parameters"] = [{"name": "uuid", "value": self.scene.suid},
                                                       {"name": "s3bucket", "value": settings.BUCKETNAME},
                                                       {"name": "parameters", "value": json.dumps(self.scene.parameters)}]

        # Call celery create task
        result = do_argo_create.apply_async(args=(template,),
                                            expires=settings.TASK_EXPIRE_TIME)
        self.task_starttime = now()
        self.cluster_log += "{} | Created \n".format(self.task_starttime)
        self.task_uuid = result.id
        self.save()

    def remove_workflow(self):
        # Catch removing unfinished workflow
        # if self.cluster_state not in Workflow.FINISHED:
            # logging.warning("Can't remove unfinished workflow")
            # return

        result = do_argo_remove.apply_async(
            args=("{}".format(self.name),),
            expires=settings.TASK_EXPIRE_TIME
        )

        self.task_starttime = now()
        self.cluster_log += "{} | Removed \n".format(self.task_starttime)

        # TODO Calculate total running time, but with a end date! 

        self.task_uuid = result.id
        self.save()

    def update_log(self):
        # return if container still has an active task
        if self.task_uuid is not None:
            return

        if self.cluster_state != 'running':
            return  # the container is done, no logging needed

        result = get_kube_log.apply_async(args=(self.name,),
                                            expires=settings.TASK_EXPIRE_TIME)
        self.task_starttime = now()
        self.task_uuid = result.id
        self.save()

    def __unicode__(self):
        return "Workflow of scene {}".format(self.scene.name)
