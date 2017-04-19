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
import zipfile

from celery.result import AsyncResult

from django.conf import settings  # noqa
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now

from model_utils import Choices

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_groups_with_perms
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import remove_perm

from jsonfield import JSONField
# from django.contrib.postgres.fields import JSONField  # When we use
# Postgresql 9.4

from delft3dworker.utils import log_progress_parser, version_default, get_version

from delft3dcontainermanager.tasks import do_docker_create
from delft3dcontainermanager.tasks import do_docker_remove
from delft3dcontainermanager.tasks import do_docker_start
from delft3dcontainermanager.tasks import do_docker_stop
from delft3dcontainermanager.tasks import get_docker_log


# ################################### SCENARIO, SCENE & CONTAINER

class Scenario(models.Model):

    """
    Scenario model
    """

    name = models.CharField(max_length=256)

    template = models.ForeignKey('Template', blank=True, null=True)

    scenes_parameters = JSONField(blank=True)
    parameters = JSONField(blank=True)

    owner = models.ForeignKey(User, null=True)

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

    def redo_proc(self, user):
        for scene in self.scene_set.all():
            if user.has_perm('delft3dworker.change_scene', scene):
                scene.redo_proc()
        return "started"

    def redo_postproc(self, user):
        for scene in self.scene_set.all():
            if user.has_perm('delft3dworker.change_scene', scene):
                scene.redo_postproc()
        return "started"

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

    def _update_state_and_save(self):

        count = self.scene_set.all().count()

        self.state = 'inactive'

        if count > 0:

            progress = 0

            for scene in self.scene_set.all():

                progress = progress + scene.progress

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

    date_created = models.DateTimeField(default=now, blank=True)
    date_started = models.DateTimeField(blank=True, null=True)

    fileurl = models.CharField(max_length=256)
    info = JSONField(blank=True)
    parameters = JSONField(blank=True)  # {"dt":20}
    state = models.CharField(max_length=256, default="CREATED")
    progress = models.IntegerField(default=0)
    task_id = models.CharField(max_length=256, blank=True)

    # TODO: use FilePath Field
    workingdir = models.CharField(max_length=256)
    parameters_hash = models.CharField(max_length=64, blank=True)

    shared_choices = [('p', 'private'), ('c', 'company'), ('w', 'world')]
    shared = models.CharField(max_length=1, choices=shared_choices)
    owner = models.ForeignKey(User, null=True)

    workflows = Choices(
        (0, 'main', 'main workflow'),
        (1, 'redo_proc', 'redo processing workflow'),
        (2, 'redo_postproc', 'redo postprocessing workflow')
    )

    workflow = models.PositiveSmallIntegerField(
        default=workflows.main, choices=workflows)

    phases = Choices(
        # Create container models
        (0, 'new', 'New'),

        # Preprocessing container
        (2, 'preproc_create', 'Allocating preprocessing resources'),
        (3, 'preproc_start', 'Starting preprocessing'),
        (4, 'preproc_run', 'Running preprocessing'),
        (5, 'preproc_fin', 'Finished preprocessing'),

        # User input wait phase
        (6, 'idle', 'Idle: waiting for user input'),

        # Simulation container
        (10, 'sim_create', 'Allocating simulation resources'),
        (11, 'sim_start', 'Starting simulation'),
        (12, 'sim_run', 'Running simulation'),
        (15, 'sim_last_proc', 'Finishing simulation'),
        (13, 'sim_fin', 'Finished simulation'),
        (14, 'sim_stop', 'Stopping simulation'),

        # Processing container
        (60, 'proc_create', 'Allocating processing resources'),
        (61, 'proc_start', 'Starting processing'),
        (62, 'proc_run', 'Running processing'),
        (63, 'proc_fin', 'Finished processing'),

        # Postprocessing container
        (20, 'postproc_create', 'Allocating postprocessing resources'),
        (21, 'postproc_start', 'Starting postprocessing'),
        (22, 'postproc_run', 'Running postprocessing'),
        (23, 'postproc_fin', 'Finished postprocessing'),

        # Export container
        (30, 'exp_create', 'Allocating export resources'),
        (31, 'exp_start', 'Starting export'),
        (32, 'exp_run', 'Running export'),
        (33, 'exp_fin', 'Finished export'),

        # Remove containers
        (17, 'cont_rem_start', 'Starting container remove'),
        (18, 'cont_rem_run', 'Removing containers'),
        (19, 'cont_rem_fin', 'Containers removed'),

        # Sync container
        (40, 'sync_create', 'Allocating synchronization resources'),
        (41, 'sync_start', 'Started synchronization'),
        (42, 'sync_run', 'Running synchronization'),
        (43, 'sync_fin', 'Finished synchronization'),

        # Sync back simulation results to rerun processing or postprocessing
        (50, 'sync_redo_create', 'Allocating synchronization resources'),
        (51, 'sync_redo_start', 'Started synchronization'),
        (52, 'sync_redo_run', 'Running synchronization'),
        (53, 'sync_redo_fin', 'Finished synchronization'),

        # Other phases
        (500, 'fin', 'Finished'),
        (1000, 'abort_start', 'Starting Abort'),
        (1001, 'abort_run', 'Aborting'),
        (1002, 'abort_fin', 'Finished Abort'),
        (1003, 'queued', 'Queued')
    )

    phase = models.PositiveSmallIntegerField(default=phases.new, choices=phases)

    # PROPERTY METHODS

    class Meta:
        permissions = (
            ('view_scene', 'View Scene'),
        )

    def versions(self):
        version_dict = {}
        for container in self.container_set.all():
            version_dict[container.container_type] = container.version
        return version_dict

    # UI CONTROL METHODS

    def reset(self):
        # only allow a start when Scene is 'Finished'
        if self.phase == self.phases.fin:
            self.shift_to_phase(self.phases.new)   # shift to Queued
            self.date_started = None
            self.progress = 0
            self.save()

        return {"task_id": None, "scene_id": None}

    def start(self):
        # only allow a start when Scene is 'Idle'
        if self.phase == self.phases.idle:
            self.shift_to_phase(self.phases.queued)   # shift to Queued
            self.date_started = now()
            self.save()

        return {"task_id": None, "scene_id": None}

    def redo_proc(self):
        # only allow a start when Scene is 'Finished'
        if self.phase == self.phases.fin:
            # Maybe shift to seperate Que if load on Swarm is to high?
            self.shift_to_phase(self.phases.queued)
            self.workflow = self.workflows.redo_proc
            self.save()

        return {"task_id": None, "scene_id": None}

    def redo_postproc(self):
        # only allow a start when Scene is 'Finished'
        if self.phase == self.phases.fin:
            # Maybe shift to seperate Que if load on Swarm is to high
            self.shift_to_phase(self.phases.queued)
            self.workflow = self.workflows.redo_postproc
            self.save()

        return {"task_id": None, "scene_id": None}

    def abort(self):
        # Stop simulation
        if self.phase >= self.phases.sim_start and self.phase <= self.phases.sim_fin:
            self.shift_to_phase(self.phases.sim_stop)   # stop Simulation

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

        files_added = False

        for root, dirs, files in os.walk(self.workingdir):
            for f in files:
                name, ext = os.path.splitext(f)

                add = False

                # Could be dynamic or tuple of extensions
                if (
                    'export_d3dinput' in options
                ) and (
                    root.endswith('simulation')
                ) and (
                    not f.startswith('TMP')
                ) and (
                    (
                        ext in ['.bcc', '.bch', '.bct', '.bnd', '.dep', '.enc',
                                '.fil', '.grd', '.ini', '.mdf', '.mdw', '.mor',
                                '.obs', '.sed', '.sh', '.url', '.xml']
                    ) or (
                        ext.startswith('.tr')
                    )
                ):
                    add = True

                # Could be dynamic or tuple of extensions
                if (
                    'export_images' in options
                ) and (
                    ext in ['.png', '.jpg', '.gif']
                ):
                    add = True

                if 'export_thirdparty' in options and (
                        'export' in root
                ) and (
                    ext in ['.gz', ]
                ):
                    add = True

                # Zip movie
                if (
                    'export_movie' in options
                ) and (
                    ext in ['.mp4']
                ) and (
                    os.path.getsize(os.path.join(root, f)) > 0
                ):
                    add = True

                if add:
                    files_added = True
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.join(slugify(self.name),
                                            os.path.relpath(abs_path, self.workingdir))
                    zipfile.write(abs_path, rel_path)

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

            # Hack to have the "dt:20" in the correct format
            if self.parameters == "":
                self.parameters = {"delft3d": self.info}

            self.fileurl = os.path.join(
                settings.WORKER_FILEURL, str(self.suid), '')

            self.info["delta_fringe_images"] = {
                "images": [],
                "location": "process/"
            }
            self.info["channel_network_images"] = {
                "images": [],
                "location": "process/"
            }
            self.info["sediment_fraction_images"] = {
                "images": [],
                "location": "process/"
            }
            self.info["subenvironment_images"] = {
                "images": [],
                "location": "postprocess/"
            }
            self.info["logfile"] = {
                "file": "",
                "location": "simulation/"
            }
            self.info["procruns"] = 0
            self.info["postprocess_output"] = {}

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

        if self.phase == self.phases.new:

            if not self.container_set.filter(container_type='preprocess').exists():
                preprocess_container = Container.objects.create(
                    scene=self,
                    container_type='preprocess',
                    desired_state='non-existent',
                )
                preprocess_container.save()

            if not self.container_set.filter(container_type='delft3d').exists():
                delft3d_container = Container.objects.create(
                    scene=self,
                    container_type='delft3d',
                    desired_state='non-existent',
                )
                delft3d_container.save()

            if not self.container_set.filter(container_type='process').exists():
                process_container = Container.objects.create(
                    scene=self,
                    container_type='process',
                    desired_state='non-existent',
                )
                process_container.save()

            if not self.container_set.filter(container_type='export').exists():
                export_container = Container.objects.create(
                    scene=self,
                    container_type='export',
                    desired_state='non-existent',
                )
                export_container.save()

            if not self.container_set.filter(container_type='postprocess').exists():
                postprocess_container = Container.objects.create(
                    scene=self,
                    container_type='postprocess',
                    desired_state='non-existent',
                )
                postprocess_container.save()

            if not self.container_set.filter(container_type='sync_cleanup').exists():
                sync_clean_container = Container.objects.create(
                    scene=self,
                    container_type='sync_cleanup',
                    desired_state='non-existent',
                )
                sync_clean_container.save()

            if not self.container_set.filter(container_type='sync_rerun').exists():
                sync_run_container = Container.objects.create(
                    scene=self,
                    container_type='sync_rerun',
                    desired_state='non-existent',
                )
                sync_run_container.save()

            self.shift_to_phase(self.phases.preproc_create)

            return

        elif self.phase == self.phases.preproc_create:

            container = self.container_set.get(container_type='preprocess')
            container.set_desired_state('created')

            if (container.docker_state != 'non-existent'):
                self.shift_to_phase(self.phases.preproc_start)

            return

        elif self.phase == self.phases.preproc_start:

            container = self.container_set.get(container_type='preprocess')
            container.set_desired_state('running')

            if (container.docker_state == 'running'):
                self.shift_to_phase(self.phases.preproc_run)

            elif (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.preproc_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.preproc_create)
                logging.error("Lost preprocess container!")

            return

        elif self.phase == self.phases.preproc_run:

            container = self.container_set.get(container_type='preprocess')
            if (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.preproc_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.preproc_start)
                logging.error("Lost preprocess container!")

            return

        elif self.phase == self.phases.preproc_fin:

            container = self.container_set.get(container_type='preprocess')
            container.set_desired_state('non-existent')

            if (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.idle)

            return

        elif self.phase == self.phases.sim_create:

            delft3d_container = self.container_set.get(
                container_type='delft3d')
            if delft3d_container.docker_state == 'non-existent':
                delft3d_container.set_desired_state('created')

            processing_container = self.container_set.get(
                container_type='process')
            if processing_container.docker_state == 'non-existent':
                processing_container.set_desired_state('created')

            if (delft3d_container.docker_state != 'non-existent' and
                    processing_container.docker_state != 'non-existent'):
                self.shift_to_phase(self.phases.sim_start)

            return

        elif self.phase == self.phases.sim_start:

            delft3d_container = self.container_set.get(
                container_type='delft3d')
            # If we've already ran, don't start again
            if delft3d_container.docker_state == 'created':
                delft3d_container.set_desired_state('running')

            processing_container = self.container_set.get(
                container_type='process')
            processing_container.set_desired_state('running')

            if (delft3d_container.docker_state == 'running'):
                self.shift_to_phase(self.phases.sim_run)

            # If there are startup errors, the container will exit
            # before the next beat and the phase will be stuck if
            # this state is not handled explicitly.
            elif (delft3d_container.docker_state == 'exited'):
                self._local_scan_process()  # update images and logfile
                self.progress = delft3d_container.container_progress
                self.save()

                delft3d_container.set_desired_state('exited')
                processing_container.set_desired_state('exited')
                self.shift_to_phase(self.phases.sim_last_proc)

            # If container disappeared, shift back
            elif (delft3d_container.docker_state == 'non-existent' or
                  processing_container.docker_state == 'non-existent'):
                logging.error("Lost sim or process container!")
                self.shift_to_phase(self.phases.sim_create)

            return

        elif self.phase == self.phases.sim_run:

            delft3d_container = self.container_set.get(
                container_type='delft3d')
            processing_container = self.container_set.get(
                container_type='process')

            self._local_scan_process()  # update images and logfile

            self.progress = delft3d_container.container_progress
            self.save()

            if (delft3d_container.docker_state == 'exited'):
                delft3d_container.set_desired_state('exited')
                self.shift_to_phase(self.phases.sim_last_proc)

            # If container disappeared, shift back
            elif (delft3d_container.docker_state == 'non-existent' or
                  processing_container.docker_state == 'non-existent'):
                logging.error("Lost sim/process container!")
                self.shift_to_phase(self.phases.sim_create)

            return

        # Ensure one extra heartbeat to start processing one last time
        elif self.phase == self.phases.sim_last_proc:
            processing_container = self.container_set.get(
                container_type='process')

            if processing_container.docker_state == 'exited':
                processing_container.set_desired_state('exited')
                self.shift_to_phase(self.phases.sim_fin)

            elif processing_container.docker_state == 'non-existent':
                self.shift_to_phase(self.phases.sim_create)

            else:
                logging.error("Stuck in {}".format(self.phase))

        elif self.phase == self.phases.sim_fin:

            delft3d_container = self.container_set.get(
                container_type='delft3d')
            delft3d_container.set_desired_state('non-existent')

            processing_container = self.container_set.get(
                container_type='process')
            processing_container.set_desired_state('non-existent')

            if (delft3d_container.docker_state != 'non-existent'):
                self.progress = delft3d_container.container_progress
                self.save()

            else:
                self.shift_to_phase(self.phases.postproc_create)

            return

        elif self.phase == self.phases.sim_stop:

            delft3d_container = self.container_set.get(
                container_type='delft3d')
            delft3d_container.set_desired_state('exited')

            processing_container = self.container_set.get(
                container_type='process')
            processing_container.set_desired_state('exited')

            if (delft3d_container.docker_state == 'exited' and
                    processing_container.docker_state == 'exited'):
                self.shift_to_phase(self.phases.sim_fin)

            # If container disappeared, shift forward
            elif (delft3d_container.docker_state == 'non-existent' or
                    processing_container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.sim_fin)

            return

        ##########
        # REDO Processing

        elif self.phase == self.phases.proc_create:

            container = self.container_set.get(container_type='process')
            container.set_desired_state('created')

            if (container.docker_state != 'non-existent'):
                self.shift_to_phase(self.phases.proc_start)

            return

        elif self.phase == self.phases.proc_start:

            container = self.container_set.get(container_type='process')
            container.set_desired_state('running')

            if (container.docker_state == 'running'):
                self.shift_to_phase(self.phases.proc_run)

            elif (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.proc_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.proc_create)
                logging.error("Lost process container!")

            return

        elif self.phase == self.phases.proc_run:

            container = self.container_set.get(container_type='process')
            if (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.proc_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.proc_create)
                logging.error("Lost process container!")

            return

        elif self.phase == self.phases.proc_fin:

            container = self.container_set.get(container_type='process')
            container.set_desired_state('non-existent')

            # Done with redo processing, sync results
            if (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.sync_create)

            return

        #############
        # Postprocessing

        elif self.phase == self.phases.postproc_create:

            container = self.container_set.get(container_type='postprocess')
            container.set_desired_state('created')

            if (container.docker_state != 'non-existent'):
                self.shift_to_phase(self.phases.postproc_start)

            return

        elif self.phase == self.phases.postproc_start:

            container = self.container_set.get(container_type='postprocess')
            container.set_desired_state('running')

            if (container.docker_state == 'running'):
                self.shift_to_phase(self.phases.postproc_run)

            elif (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.postproc_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.postproc_create)
                logging.error("Lost postprocess container!")

            return

        elif self.phase == self.phases.postproc_run:

            container = self.container_set.get(container_type='postprocess')
            if (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.postproc_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.postproc_create)
                logging.error("Lost postprocess container!")

            return

        elif self.phase == self.phases.postproc_fin:

            container = self.container_set.get(container_type='postprocess')
            container.set_desired_state('non-existent')

            if (container.docker_state == 'non-existent'):
                self._local_scan_postprocess()  # scan for new images
                self._parse_postprocessing()  # parse output.ini
                self.shift_to_phase(self.phases.exp_create)

            return

        elif self.phase == self.phases.exp_create:

            container = self.container_set.get(container_type='export')
            container.set_desired_state('created')

            if (container.docker_state != 'non-existent'):
                self.shift_to_phase(self.phases.exp_start)

            return

        elif self.phase == self.phases.exp_start:

            container = self.container_set.get(container_type='export')
            container.set_desired_state('running')

            if (container.docker_state == 'running'):
                self.shift_to_phase(self.phases.exp_run)

            elif (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.exp_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.exp_create)
                logging.error("Lost export container!")

            return

        elif self.phase == self.phases.exp_run:

            container = self.container_set.get(container_type='export')
            if (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.exp_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.exp_create)
                logging.error("Lost export container!")

            return

        elif self.phase == self.phases.exp_fin:

            container = self.container_set.get(container_type='export')
            container.set_desired_state('non-existent')

            if (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.sync_create)  # shift to sync

            return

        elif self.phase == self.phases.cont_rem_start:

            for container in self.container_set.all():
                container.set_desired_state('non-existent')

            self.shift_to_phase(self.phases.cont_rem_run)

            return

        elif self.phase == self.phases.cont_rem_run:

            done = True
            for container in self.container_set.all():
                done = done and (container.docker_state == 'non-existent')

            if done:
                self.shift_to_phase(self.phases.cont_rem_fin)

            return

        elif self.phase == self.phases.abort_start:

            delft3d_container = self.container_set.get(
                container_type='delft3d')
            delft3d_container.set_desired_state('exited')

            processing_container = self.container_set.get(
                container_type='process')
            processing_container.set_desired_state('exited')

            self.shift_to_phase(self.phases.abort_run)

            return

        elif self.phase == self.phases.abort_run:

            delft3d_container = self.container_set.get(
                container_type='delft3d')
            processing_container = self.container_set.get(
                container_type='process')

            if (delft3d_container.docker_state == 'exited'):
                self.shift_to_phase(self.phases.abort_fin)

            return

        elif self.phase == self.phases.abort_fin:
            delft3d_container = self.container_set.get(
                container_type='delft3d')
            delft3d_container.set_desired_state('non-existent')

            processing_container = self.container_set.get(
                container_type='process')
            processing_container.set_desired_state('non-existent')

            if (delft3d_container.docker_state == 'non-existent' and
                    processing_container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.idle)

            return

        elif self.phase == self.phases.sync_create:

            container = self.container_set.get(container_type='sync_cleanup')
            container.set_desired_state('created')

            if (container.docker_state != 'non-existent'):
                self.shift_to_phase(self.phases.sync_start)

            return

        elif self.phase == self.phases.sync_start:

            container = self.container_set.get(container_type='sync_cleanup')
            container.set_desired_state('running')

            if (container.docker_state == 'running'):
                self.shift_to_phase(self.phases.sync_run)

            elif (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.sync_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.sync_create)
                logging.error("Lost sync container!")

            return

        elif self.phase == self.phases.sync_run:

            container = self.container_set.get(container_type='sync_cleanup')
            if (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.sync_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.sync_create)
                logging.error("Lost sync container!")

            return

        elif self.phase == self.phases.sync_fin:

            container = self.container_set.get(container_type='sync_cleanup')
            container.set_desired_state('non-existent')

            if (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.fin)

            return

        #############
        # REDO PHASES

        elif self.phase == self.phases.sync_redo_create:

            container = self.container_set.get(container_type='sync_rerun')
            container.set_desired_state('created')

            if (container.docker_state != 'non-existent'):
                self.shift_to_phase(self.phases.sync_redo_start)

            return

        elif self.phase == self.phases.sync_redo_start:

            container = self.container_set.get(container_type='sync_rerun')
            container.set_desired_state('running')

            if (container.docker_state == 'running'):
                self.shift_to_phase(self.phases.sync_redo_run)

            elif (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.sync_redo_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.sync_redo_create)
                logging.error("Lost sync_rerun container!")

            return

        elif self.phase == self.phases.sync_redo_run:

            container = self.container_set.get(container_type='sync_rerun')
            if (container.docker_state == 'exited'):
                container.set_desired_state('exited')
                self.shift_to_phase(self.phases.sync_redo_fin)

            # If container disappeared, shift back
            elif (container.docker_state == 'non-existent'):
                self.shift_to_phase(self.phases.sync_redo_create)
                logging.error("Lost sync_rerun container!")

            return

        elif self.phase == self.phases.sync_redo_fin:

            container = self.container_set.get(container_type='sync_rerun')
            container.set_desired_state('non-existent')

            # If sync for rerun is finished, shift to postporcessing phase from
            # the "default" workflow.
            if (container.docker_state == 'non-existent'):
                if self.workflow == self.workflows.redo_proc:
                    self.shift_to_phase(self.phases.proc_create)
                if self.workflow == self.workflows.redo_postproc:
                    self.shift_to_phase(self.phases.postproc_create)

            return

        #############
        # QUEUED

        elif self.phase == self.phases.queued:

            scene_phases = Scene.objects.values_list('phase', flat=True)

            number_simulations = sum(
                (i >= self.phases.sim_create and i <= self.phases.sim_stop) for i in scene_phases)

            if number_simulations < settings.MAX_SIMULATIONS:
                if self.workflow == self.workflows.main:
                    self.shift_to_phase(self.phases.sim_create)
                elif (self.workflow == self.workflows.redo_proc or
                      self.workflow == self.workflows.redo_postproc):
                    self.shift_to_phase(self.phases.sync_redo_create)

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

    def _local_scan_postprocess(self):
        for root, dirs, files in os.walk(
            os.path.join(self.workingdir, 'postprocess')
        ):
            for f in sorted(files):
                name, ext = os.path.splitext(f)
                if ext in ('.png', '.jpg', '.gif'):
                    # TODO use get to check image list and
                    # make this code less deep in if/for statements
                    if ("subenvironment" in name and
                        f not in self.info[
                            "subenvironment_images"]["images"]):
                        self.info["subenvironment_images"][
                            "images"].append(f)
                    else:
                        # Other images ?
                        pass
        self.save()

    # Run this after post processing
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

    scene = models.ForeignKey(Scene)

    task_uuid = models.UUIDField(
        default=None, blank=True, null=True)
    task_starttime = models.DateTimeField(default=now, blank=True)

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

    container_starttime = models.DateTimeField(default=now, blank=True)
    container_stoptime = models.DateTimeField(default=now, blank=True)
    container_exitcode = models.PositiveSmallIntegerField(default=0)
    container_progress = models.PositiveSmallIntegerField(default=0)

    docker_log = models.TextField(blank=True, default='')
    container_log = models.TextField(blank=True, default='')

    version = JSONField(default=version_default)

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
                           'folders': [simdir],  # sync doesn't need new folders
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

        self.version = get_version(self.container_type)
        kwargs[self.container_type]['environment'].update(self.version)

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
    templates = JSONField(default='[]')
    sections = JSONField(default='[]')

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
    meta = JSONField(blank=True)
    sections = JSONField(blank=True)

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

    class Meta:
        permissions = (
            ('view_template', 'View Template'),
        )
