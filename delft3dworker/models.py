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
from django.core.files.base import ContentFile
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

from delft3dcontainermanager.tasks import get_argo_workflows, do_argo_create
from delft3dcontainermanager.tasks import do_argo_remove, get_kube_log


# ################################### VERSION_SVN, SCENARIO, SCENE & CONTAINER


def default_svn_version():
    """Placeholder for old migrations."""
    pass


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

    # Entrypoints for workflow, not used yet
    entrypoints = Choices(
        (0, 'main', 'main workflow'),
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

    # PROPERTY METHODS

    class Meta:
        permissions = (
            ('view_scene', 'View Scene'),
        )

    # UI CONTROL METHODS

    def reset(self):
        return self.redo()

    def start(self):
        # only allow a start when Scene is 'Idle'
        if self.phase == self.phases.idle:
            self.shift_to_phase(self.phases.sim_start)
            self.date_started = tz_now()
            self.save()

        return {"task_id": None, "scene_id": None}

    def redo(self):
        # only allow a redo when Scene is 'Finished'
        if self.phase == self.phases.fin:
            self.date_started = tz_now()
            self.shift_to_phase(self.phases.sim_start)
            self.workflow.progress = 0
            self.progress = 0
            self.save()

        return {"task_id": None, "scene_id": None}

    def abort(self):
        # Stop simulation
        if self.phase >= self.phases.sim_start and self.phase <= self.phases.sim_fin:
            self.shift_to_phase(self.phases.sim_fin)   # stop Simulation

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

            self.info = Template.INFO

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
            if (self.workflow.cluster_state in Workflow.FINISHED):
                self.shift_to_phase(self.phases.sim_fin)

            # If workflow disappeared, shift back
            elif (self.workflow.cluster_state == 'non-existent'):
                logging.error("Lost workflow in cluster!")
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
    # TODO Determine post processing step in workflow
    # Now this runs every processing loop
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
    # TODO Base this on fixtures
    INFO = {
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
        "logfile": {"file": ""},
    }
    info = JSONField(blank=True, default=INFO)
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
    # name combines shortname of linked Template and the scene suid
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
        time_passed = now() - self.task_starttime
        if result.ready():

            if result.successful():
                # Log parsing
                if "get_kube_log" in result.result:
                    log = result.result["get_kube_log"]

                    self.cluster_log += "---------\n"
                    self.cluster_log += log

                    progress = log_progress_parser(log, "delft3d")
                    if progress is not None:
                        self.progress = math.ceil(progress)

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
            if state == "Failed" or state == "Error":
                logging.error("{} failed!".format(self.name))
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

        self.yaml.save("{}.yaml".format(self.name), ContentFile(yaml.dump(template)), save=False)

        # Call celery create task
        result = do_argo_create.apply_async(args=(template,),
                                            expires=settings.TASK_EXPIRE_TIME)
        self.task_starttime = now()
        self.action_log += "{} | Created \n".format(self.task_starttime)
        self.task_uuid = result.id
        self.save()

    def remove_workflow(self):
        # Catch removing unfinished workflow
        if self.cluster_state not in Workflow.FINISHED:
            logging.warning("Can't remove unfinished workflow")
            return

        result = do_argo_remove.apply_async(
            args=(self.name,),
            expires=settings.TASK_EXPIRE_TIME
        )

        self.task_starttime = now()
        self.action_log += "{} | Removed \n".format(self.task_starttime)

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
