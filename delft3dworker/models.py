from __future__ import absolute_import

import ConfigParser
import copy
import io
import logging
import os
import uuid
import zipfile

from celery.contrib.abortable import AbortableAsyncResult
from celery.result import AsyncResult
from celery.exceptions import TimeoutError
from celery.task.control import revoke as revoke_task

from datetime import datetime

from delft3dworker.tasks import chainedtask
from delft3dworker.utils import compare_states, parse_info

from django.conf import settings  # noqa
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.db import models

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_groups_with_perms
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import remove_perm

from jsonfield import JSONField
# from django.contrib.postgres.fields import JSONField  # When we use
# Postgresql 9.4

from mako.template import Template as MakoTemplate

from shutil import copystat
from shutil import copytree
from shutil import copyfile
from shutil import rmtree

import hashlib

BUSYSTATE = "PROCESSING"


# ################################### SCENARIO

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
    def _update_state(self):
        # All states from its scenes
        states = [scene.state for scene in self.scene_set.all()]
        self.state = compare_states(*states)

        # All progress from its scenes
        progs = [scene.progress for scene in self.scene_set.all()]
        self.progress = sum(progs) / len(progs) if len(progs) != 0 else 0

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


# SCENE


class Scene(models.Model):

    """
    Scene model
    """

    name = models.CharField(max_length=256)

    # suid = models.CharField(max_length=256, editable=False)
    suid = models.UUIDField(default=uuid.uuid4, editable=False)

    scenario = models.ManyToManyField(Scenario, blank=True)

    fileurl = models.CharField(max_length=256)
    info = JSONField(blank=True)
    parameters = JSONField(blank=True)  # {"dt":20}
    state = models.CharField(max_length=256, default="CREATED")
    progress = models.IntegerField(default=0)
    task_id = models.CharField(max_length=256)

    # Please use FilePath Field
    workingdir = models.CharField(max_length=256)
    parameters_hash = models.CharField(max_length=64, blank=True)

    shared_choices = [('p', 'private'), ('c', 'company'), ('w', 'world')]
    shared = models.CharField(max_length=1, choices=shared_choices)
    owner = models.ForeignKey(User, null=True)

    # PROPERTY METHODS
    class Meta:
        permissions = (
            ('view_scene', 'View Scene'),
        )

    # CONTROL METHODS

    def start(self, workflow="main"):

        # Check if task is already start
        if self.task_id != "":
            result = AbortableAsyncResult(self.task_id)

            # Find out state
            if result.state == "PENDING":
                return {"error": "task already PENDING", "task_id": self.task_id}
            elif result.state == BUSYSTATE:
                return {"error": "task already BUSY", "task_id": self.task_id}
            else:
                return {"error": "task already STARTED", "task_id": self.task_id}

        # Task has not yet been started
        else:
            result = chainedtask.delay(
                self.parameters, self.workingdir, workflow)
            self.task_id = result.task_id  # so we can't start again

            self._update_state()  # will save for us

            return {"task_id": self.task_id, "scene_id": self.suid}

    def abort(self):
        """Function called on stop in frontend, hence the json response."""
        result = AbortableAsyncResult(self.task_id)

        # If not running, revoke task
        if not result.state == BUSYSTATE:
            # thou shalt not terminate
            revoke_task(self.task_id, terminate=False)
            self.state = "REVOKED"
        else:
            result.abort()
            self.state = "ABORTED"

        self._update_state()  # will save for us

        return {
            "task_id": self.task_id,
            "state": result.state,
            "info": str(self.info)
        }

    def export(self, options):
        # Alternatives to this implementation are:
        # - django-zip-view (sets mimetype and content-disposition)
        # - django-filebrowser (filtering and more elegant browsing)

        # from:
        # http://stackoverflow.com/questions/67454/serving-dynamically-generated-zip-archives-in-django

        zip_filename = 'export.zip'

        # Open BytesIO to grab in-memory ZIP contents
        # (be explicit about bytes)
        stream = io.BytesIO()

        # The zip compressor
        zf = zipfile.ZipFile(stream, "w")

        # Add files here.
        # If you run out of memory you have 2 options:
        # - stream
        # - zip in a subprocess shell with zip
        # - zip to temporary file
        for root, dirs, files in os.walk(self.workingdir):
            for f in files:
                name, ext = os.path.splitext(f)

                # Could be dynamic or tuple of extensions
                if (
                    'export_images' in options
                ) and (
                    ext in ['.png', '.jpg', '.gif']
                ):
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, self.workingdir)
                    zf.write(abs_path, rel_path)

                if (
                    'export_input' in options
                ) and (
                    "simulation" in root
                ) and (
                    name == 'a'
                ):
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, self.workingdir)
                    zf.write(abs_path, rel_path)

                if 'export_thirdparty' in options and (
                        'export' in root):
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, self.workingdir)
                    zf.write(abs_path, rel_path)

                # Zip movie
                if (
                    'export_movie' in options
                ) and (
                    ext in ['.mp4']
                ) and (
                    os.path.getsize(os.path.join(root, f)) > 0
                ):
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
                settings.WORKER_FILEDIR, str(self.suid), '')
            self._create_datafolder()

            # Hack to have the "dt:20" in the correct format
            if self.parameters == "":
                self.parameters = {"delft3d": self.info}

            self._create_ini()

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

    # INTERNALS

    def _create_datafolder(self):
        # create directory for scene
        if not os.path.exists(self.workingdir):
            os.makedirs(self.workingdir, 02775)

            folders = ['process', 'preprocess', 'simulation', 'export']

            for f in folders:
                os.makedirs(os.path.join(self.workingdir, f))

    def _delete_datafolder(self):
        # delete directory for scene
        if os.path.exists(self.workingdir):
            try:
                rmtree(self.workingdir)
            except:
                # Files written by root can't be deleted by django
                logging.error("Failed to delete working directory")

    def _create_ini(self):
        # create ini file for containers
        # in 2.7 ConfigParser is a bit stupid
        # in 3.x configparser has .read_dict()
        config = ConfigParser.SafeConfigParser()
        for section in self.parameters:
            if not config.has_section(section):
                config.add_section(section)
            for key, value in self.parameters[section].items():

                # TODO: find more elegant solution for this! ugh!
                if not key == 'units':
                    if not config.has_option(section, key):
                        config.set(*map(str, [section, key, value]))

        with open(os.path.join(self.workingdir, 'input.ini'), 'w') as f:
            config.write(f)  # Yes, the ConfigParser writes to f

        copyfile(
            os.path.join(self.workingdir, 'input.ini'),
            os.path.join(os.path.join(
                self.workingdir, 'preprocess/' 'input.ini'))
        )
        copyfile(
            os.path.join(self.workingdir, 'input.ini'),
            os.path.join(os.path.join(
                self.workingdir, 'simulation/' 'input.ini'))
        )
        copyfile(
            os.path.join(self.workingdir, 'input.ini'),
            os.path.join(os.path.join(
                self.workingdir, 'process/' 'input.ini'))
        )

    def _update_state(self):
        # only retrieve state if it has a task_id
        # (which means the task is started)
        if self.task_id != '':
            result = AbortableAsyncResult(self.task_id)

            # parse result and compare with current stored info
            info = result.info if isinstance(
                result.info, dict) else {"info": str(result.info)}
            # Parse info from chainedtask
            self.progress, self.state, info = parse_info(info)

            # Update model
            if 'procruns' in self.info and 'procruns' in info:
                processed = info['procruns'] > self.info['procruns']
            else:
                processed = False
            self.info.update(info)
        else:
            return self.state

        # Only check for new images
        # when new processing has run
        if processed:
            for root, dirs, files in os.walk(
                os.path.join(self.workingdir, 'process')
            ):
                for f in sorted(files):
                    name, ext = os.path.splitext(f)
                    if ext in ('.png', '.jpg', '.gif'):
                        if "delta_fringe" in name:
                            self.info["delta_fringe_images"][
                                "images"].append(f)
                        elif "channel_network" in name:
                            self.info["channel_network_images"][
                                "images"].append(f)
                        elif "sediment_fraction" in name:
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

        self.save()
        return self.state

    def __unicode__(self):
        return self.name


# ################################### Template

class SearchForm(models.Model):

    """
    SearchForm model:
    This model is used to make a search form similar to the Template model.
    The idea was to provide a json to the front-end similar to how we deliver
    the Templates: via the API.
    Possible improvements: Becuase we only have one SearchForm, we could
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
