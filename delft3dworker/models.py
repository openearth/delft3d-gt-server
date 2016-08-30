from __future__ import absolute_import

import copy
from datetime import datetime
import hashlib
import io
import logging
import os
import shutil
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

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_groups_with_perms
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import remove_perm

from jsonfield import JSONField
# from django.contrib.postgres.fields import JSONField  # When we use
# Postgresql 9.4

from delft3dworker.utils import compare_states
from delft3dworker.utils import parse_info

from delft3dcontainermanager.tasks import do_docker_create
from delft3dcontainermanager.tasks import do_docker_remove
from delft3dcontainermanager.tasks import do_docker_start
from delft3dcontainermanager.tasks import do_docker_stop
from delft3dcontainermanager.tasks import get_docker_log


BUSYSTATE = "PROCESSING"


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

    def start(self, user, workflow="main"):
        for scene in self.scene_set.all():
            if user.has_perm('delft3dworker.change_scene', scene):
                scene.start(workflow)
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

        # TODO rewrite _update_state_and_save method+

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

    phases = (
        (0, 'New'),
        (1, 'Creating containers...'),
        (2, 'Created containers'),
        (3, 'Starting preprocessing...'),
        (4, 'Running preprocessing...'),
        (5, 'Finished preprocessing'),
        (6, 'Idle'),
        (7, 'Starting simulation...'),
        (8, 'Running simulation...'),
        (9, 'Finished simulation'),
        (10, 'Starting postprocessing...'),
        (11, 'Running postprocessing...'),
        (12, 'Finished postprocessing'),
        (13, 'Starting container remove...'),
        (14, 'Removing containers...'),
        (15, 'Containers removed'),

        (1000, 'Starting Abort...'),
        (1001, 'Aborting...'),
        (1002, 'Finished Abort'),
    )
    phase = models.PositiveSmallIntegerField(default=0, choices=phases)

    # PROPERTY METHODS

    class Meta:
        permissions = (
            ('view_scene', 'View Scene'),
        )

    # UI CONTROL METHODS

    def start(self, workflow="main"):

        if self.phase == 6:  # only allow a start when Scene is 'Idle'
            self.shift_to_phase(7)   # shift to Starting simulation...

        return {"task_id": None, "scene_id": None}

    def abort(self):

        if self.phase >= 8:  # only allow aborts when simulation (or more)
            self.shift_to_phase(1000)   # shift to Aborting...

        return {
            "task_id": None,
            "state": None,
            "info": None
        }

    def export(self, options):
        # Alternatives to this implementation are:
        # - django-zip-view (sets mimetype and content-disposition)
        # - django-filebrowser (filtering and more elegant browsing)

        # from:
        # http://stackoverflow.com/questions/67454/serving-dynamically-generated-zip-archives-in-django

        zip_filename = '{}.zip'.format(slugify(self.name))

        # Open BytesIO to grab in-memory ZIP contents
        # (be explicit about bytes)
        stream = io.BytesIO()

        # The zip compressor
        zf = zipfile.ZipFile(stream, "w", zipfile.ZIP_STORED, True)

        # Add files here.
        # If you run out of memory you have 2 options:
        # - stream
        # - zip in a subprocess shell with zip
        # - zip to temporary file
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
                    ext in ['.bcc', '.bch', '.bct', '.bnd', '.dep', '.enc',
                            '.fil', '.grd', '.ini', '.mdf', '.mdw', '.mor',
                            '.obs', '.sed', '.sh', '.tr1', '.url', '.xml']
                ):
                    add = True

                # Could be dynamic or tuple of extensions
                if (
                    'export_d3doutput' in options
                ) and (
                    root.endswith('simulation')
                ) and (
                    not f.startswith('TMP')
                ) and (
                    ext in ['.dat', '.def', '.nc']
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
                        'export' in root):
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
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, self.workingdir)
                    zf.write(abs_path, rel_path)

        # Must close zip for all contents to be written
        zf.close()
        return stream, zip_filename

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
            self.info["logfile"] = {
                "file": "",
                "location": "simulation/"
            }
            self.info["procruns"] = 0

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

        # ### PHASE: New
        if self.phase == 0:

            # what do we do? - create containers
            preprocess_container = Container.objects.create(
                scene=self,
                container_type='preprocess',
                desired_state='created',
            )
            preprocess_container.save()
            delft3d_container = Container.objects.create(
                scene=self,
                container_type='delft3d',
                desired_state='created',
            )
            delft3d_container.save()
            process_container = Container.objects.create(
                scene=self,
                container_type='process',
                desired_state='created',
            )
            process_container.save()

            # when do we shift? - always
            self.shift_to_phase(1)  # shift to Creating...

            return

        # ### PHASE: Creating...
        if self.phase == 1:

            # what do we do? - and now we wait...

            # when do we shift? - when all containers are created
            done = True
            for container in self.container_set.all():
                done = done and (container.docker_state == 'created')

            if done:
                self.shift_to_phase(2)  # shift to Created containers

        # ### PHASE: Created containers
        if self.phase == 2:

            # what do we do? - nothing

            # when do we shift? - always
            self.shift_to_phase(3)  # shift to Starting preprocessing...

            return

        # ### PHASE: Starting preprocessing...
        if self.phase == 3:

            # what do we do? - tell preprocess to start
            container = self.container_set.get(container_type='preprocess')
            container.set_desired_phase('running')

            # when do we shift? - preprocess is running
            if (container.docker_state == 'running'):
                self.shift_to_phase(4)  # shift to Running preprocessing...

            return

        # ### PHASE: Running preprocessing...
        if self.phase == 4:

            # what do we do? - and now we wait...

            # when do we shift? - preprocess is done
            container = self.container_set.get(container_type='preprocess')
            if (container.docker_state == 'exited'):
                container.set_desired_phase('exited')
                self.shift_to_phase(5)  # shift to Created containers

            return

        # ### PHASE: Finished preprocessing
        if self.phase == 5:

            # what do we do? - nothing

            # when do we shift? - preprocess is done
            self.shift_to_phase(6)  # shift to Idle

            return

        # ### PHASE: Starting simulation...
        if self.phase == 7:

            # what do we do? - tell simulation containers to start
            delft3d_container = self.container_set.get(
                container_type='delft3d')
            delft3d_container.set_desired_phase('running')

            processing_container = self.container_set.get(
                container_type='process')
            processing_container.set_desired_phase('running')

            # when do we shift? - simulation containers are running
            if (delft3d_container.docker_state == 'running'):
                self.shift_to_phase(8)  # shift to Running simulation...

            return

        # ### PHASE: Running simulation...
        if self.phase == 8:

            # what do we do? - and now we wait...

            # when do we shift? - simulations containers are done
            delft3d_container = self.container_set.get(
                container_type='delft3d')
            processing_container = self.container_set.get(
                container_type='process')

            if (delft3d_container.docker_state == 'exited'):
                delft3d_container.set_desired_phase('exited')
                processing_container.set_desired_phase('exited')

                self.shift_to_phase(9)  # shift to Finished simulation

            return

        # ### PHASE: Finished simulation
        if self.phase == 9:

            # what do we do? - nothing

            # when do we shift? - always
            self.shift_to_phase(6)  # shift to Idle

            return

        # ### PHASE: Starting container remove...
        if self.phase == 13:

            # what do we do? - tell containers to harakiri
            for container in self.container_set.all():
                container.set_desired_phase('non-existent')

            # when do we shift? - always
            self.shift_to_phase(14)  # Removing containers...

            return

        # ### PHASE: Removing containers...
        if self.phase == 14:

            # what do we do? - and now we wait...

            # when do we shift? - containers are gone
            done = True
            for container in self.container_set.all():
                done = done and (container.docker_state == 'non-existent')

            if done:
                self.shift_to_phase(15)  # shift to Containers removed

            return

        # ### PHASE: Starting Abort...
        if self.phase == 1000:

            # what do we do? - tell containers to stop
            delft3d_container = self.container_set.get(
                container_type='delft3d')
            delft3d_container.set_desired_phase('exited')

            processing_container = self.container_set.get(
                container_type='process')
            processing_container.set_desired_phase('exited')

            # when do we shift? - always
            self.shift_to_phase(1001)  # shift to Aborting...

            return

        # ### PHASE: Aborting...
        if self.phase == 1001:

            # what do we do? - and now we wait...

            # when do we shift? - containers are gone
            delft3d_container = self.container_set.get(
                container_type='delft3d')
            processing_container = self.container_set.get(
                container_type='process')

            if (delft3d_container.docker_state == 'exited'):
                delft3d_container.set_desired_phase('exited')
                processing_container.set_desired_phase('exited')

                self.shift_to_phase(1002)  # shift to Finished Aborting

            return

        # ### PHASE: Finished Aborting
        if self.phase == 1002:

            # what do we do? - nothing

            # when do we shift? - always
            self.shift_to_phase(6)  # shift to Idle

            return

        return

    def shift_to_phase(self, new_phase):
        self.phase = new_phase
        self.save()

    # INTERNALS

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

    task_starttime = models.DateTimeField(default=now(), blank=True)

    # delft3dgtmain.provisionedsettings
    CONTAINER_TYPE_CHOICES = (
        ('preprocess', 'preprocess'),
        ('delft3d', 'delft3d'),
        ('process', 'process'),
        ('postprocess', 'postprocess'),
        ('export', 'export'),
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

    docker_log = models.TextField(blank=True, default='')

    # container_starttime = models.DateTimeField()
    # container_stoptime = models.DateTimeField()

    # CONTROL METHODS

    def set_desired_phase(self, desired_state):

        if desired_state < 1000 and self.phase != 6:
            return

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

        print result
        print result.ready()
        print result.get()

        if result.ready():

            if result.successful():
                docker_id, docker_log = result.result

                # only write the id if the result is as expected
                if docker_id is not None and isinstance(docker_id, str):
                    self.docker_id = docker_id
                else:
                    logging.warn(
                        "Task of Container [{}] returned an unexpected "
                        "docker_id: {}".format(self, docker_id))

                # only write the log if the result is as expected and there is
                # an actual log
                if docker_log is not None and isinstance(
                        docker_id, unicode) and docker_log != '':
                    self.docker_log = docker_log

            else:
                error = result.result
                logging.warn(
                    "Task of Container [{}] resulted in {}: {}".
                    format(self, result.state, error))

            self.task_uuid = None
            self.save()

        elif result.state == "PENDING":
            logging.warn("Celery task is still not ready, removing from db.")
            result.revoke()
            self.task_uuid = None

        # elif self.task_starttime - now() > 500:
            # #task expired here
            # result.revoke()
            # self.task_uuid = None

        else:
            logging.warn("Celery task of {} is not ready yet.".format(self))

    def update_from_docker_snapshot(self, snapshot):
        """
        Update the Container based on a given snapshot of a docker container
        which was retrieved with docker-py's client.containers(all=True)
        (equivalent to 'docker ps').

        Given that the container has no pending tasks, Compare this state to
        the its desired_state, which is defined by the Scene to which this
        Container belongs. If (for any reason) the docker_state is different
        from the desired_state, act: start a task to get both states matched.

        At the end request a log update.
        """

        self._update_state_and_save(snapshot)

        self._fix_state_mismatch()

        self._update_log()

    # INTERNALS

    def _update_state_and_save(self, snapshot):
        """
        Var snapshot can be either dictionary or None.
        If None: docker container does not exist
        If dictionary: snapshot['Status'] is a string describing status
        """

        if snapshot is None:
            self.docker_state = 'non-existent'
            self.docker_id = ''

        elif isinstance(snapshot, dict) and ('State' in snapshot):

            choices = [choice[1] for choice in self.CONTAINER_STATE_CHOICES]
            if snapshot['State'] in choices:
                self.docker_state = snapshot['State']

            elif snapshot['Status'].startswith('Up'):
                self.docker_state = 'running'

            elif snapshot['Status'].startswith('Created'):
                self.docker_state = 'created'

            elif snapshot['Status'].startswith('Exited'):
                self.docker_state = 'exited'

            elif snapshot['Status'].startswith('Dead'):
                self.docker_state = 'exited'

            elif snapshot['Status'].startswith('Removal In Progress'):
                self.docker_state = 'running'

            else:
                logging.error(
                    'received unknown docker Status: {}'.format(
                        snapshot['Status']
                    )
                )
                self.docker_state = 'unknown'

        else:
            logging.error('received unknown snapshot: {}'.format(snapshot))
            self.docker_state = 'unknown'

        self.save()

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

        # Specific settings for each container type
        # TODO It would be more elegant to put these
        # hardcoded settings in a seperate file.
        kwargs = {
            'delft3d': {'image': settings.DELFT3D_IMAGE_NAME,
                        'volumes': ['{0}:/data'.format(simdir)],
                        'folders': [simdir],
                        'command': ""},

            'export': {'image': settings.EXPORT_IMAGE_NAME,
                       'volumes': [
                           '{0}:/data/output:z'.format(expdir),
                           '{0}:/data/input:ro'.format(simdir)],
                       'folders': [expdir,
                                   simdir],
                       'command': "/data/run.sh /data/svn/scripts/export/"
                       "export2grdecl.py",
                       },

            'postprocess': {'image': settings.POSTPROCESS_IMAGE_NAME,
                            'volumes': [
                                '{0}:/data/output:z'.format(posdir),
                                '{0}:/data/input:ro'.format(workingdir)],
                            'folders': [workingdir,
                                        posdir],
                            'command': "",
                            },

            'preprocess': {'image': settings.PREPROCESS_IMAGE_NAME,
                           'volumes': [
                               '{0}:/data/output:z'.format(simdir),
                               '{0}:/data/input:ro'.format(predir)],
                           'folders': [predir,
                                       simdir],
                           'command': "/data/run.sh /data/svn/scripts/"
                           "preprocessing/preprocessing.py"
                           },

            'process': {'image': settings.PROCESS_IMAGE_NAME,
                        'volumes': [
                            '{0}:/data/input:ro'.format(simdir),
                            '{0}:/data/output:z'.format(prodir)
                        ],
                        'folders': [prodir,
                                    simdir],
                        'command': ' '.join([
                            "/data/run.sh ",
                            "/data/svn/scripts/postprocessing/"
                            "channel_network_proc.py",
                            "/data/svn/scripts/postprocessing/"
                            "delta_fringe_proc.py",
                            "/data/svn/scripts/postprocessing/"
                            "sediment_fraction_proc.py",
                            "/data/svn/scripts/visualisation/"
                            "channel_network_viz.py",
                            "/data/svn/scripts/visualisation/"
                            "delta_fringe_viz.py",
                            "/data/svn/scripts/visualisation/"
                            "sediment_fraction_viz.py"
                        ])},
        }

        parameters = self.scene.parameters
        environment = {"uuid": str(self.scene.suid)}
        label = {"type": self.container_type}

        result = do_docker_create.delay(label, parameters, environment,
                                        **kwargs[self.container_type])

        self.task_starttime = now()
        self.task_uuid = result.id
        self.save()

    def _start_container(self):
        # a container can only be started if it is in 'created' or 'exited'
        # state, any other state we will not allow a start
        if self.docker_state != 'created' and self.docker_state != 'exited':
            logging.info('Trying to start a container in "{}" state: ignoring '
                         'command.'.format(self.docker_state))
            return  # container is not ready for start

        result = do_docker_start.delay(self.docker_id)
        self.task_starttime = now()
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

        result = do_docker_stop.delay(self.docker_id)
        self.task_starttime = now()
        self.task_uuid = result.id
        self.save()

    def _remove_container(self):
        # a container can only be removed if it is in 'created' or 'exited'
        # state, any other state we will not allow a remove
        if self.docker_state != 'created' and self.docker_state != 'exited':
            logging.info('Trying to remove a container in "{}" state: ignoring'
                         ' command.'.format(self.docker_state))
            return  # container not ready for delete

        result = do_docker_remove.delay(self.docker_id)
        self.task_starttime = now()
        self.task_uuid = result.id

    def _update_log(self):
        # return if container still has an active task
        if self.task_uuid is not None:
            return

        if self.docker_state != 'running':
            return  # the container is done, no logging needed

        result = get_docker_log.delay(self.docker_id)
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

    def save(self, *args, **kwargs):
        returnval = super(Template, self).save(*args, **kwargs)

        # update the MAIN search form after any template save
        searchform, created = SearchForm.objects.get_or_create(name="MAIN")
        searchform.update()

        return returnval

    def __unicode__(self):
        return self.name

    class Meta:
        permissions = (
            ('view_template', 'View Template'),
        )
