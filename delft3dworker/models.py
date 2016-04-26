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

from django.conf import settings  # noqa
from django.core.urlresolvers import reverse_lazy
from django.db import models

from jsonfield import JSONField

from mako.template import Template as MakoTemplate

from shutil import copystat
from shutil import copytree
from shutil import rmtree


BUSYSTATE = "PROCESSING"


# ################################### SCENARIO

class Scenario(models.Model):

    """
    Scenario model
    """

    name = models.CharField(max_length=256)

    template = models.OneToOneField('Template', null=True)

    parameters = JSONField(blank=True)

    # PROPERTY METHODS

    def get_absolute_url(self):

        return "{0}?id={1}".format(reverse_lazy('scenario_detail'), self.id)

    def serialize(self):
        return {
            "template": self.template,
            "name": self.name,
            "parameters": self.parameters,
            "scenes": self.scene_set.all(),
            "id": self.id
        }

    def load_settings(self, settings):
        self.parameters = [{}]

        for key, value in settings.items():
            self._parse_setting(key, value)

        # debugging output
        # for value in self.parameters:

        self.save()

    def createscenes(self):
        for i, sceneparameters in enumerate(self.parameters):
            scene = Scene(name="{}: Scene {}".format(
                self.name, i), scenario=self, parameters=sceneparameters)
            scene.save()
        self.save()

    # CONTROL METHODS

    def start(self):
        for scene in self.scene_set.all():
            scene.start()
        return "started"

    def stop(self):
        for scene in self.scene_set.all():
            scene.abort()
        return "stopped"

    # INTERNALS

    def _parse_setting(self, key, setting):

        if not ('value' in setting or 'valid' in settings or setting['valid']):
            return

        if key == "scenarioname":
            self.name = setting['value']
            return

        if not setting["useautostep"]:
            # No autostep, just add these settings
            for scene in self.parameters:
                if key not in scene:
                    scene[key] = setting
        else:
            # Autostep! Run past all parameter scenes, iteratively
            minstep = float(setting["minstep"])
            maxstep = float(setting["maxstep"])
            step = float(setting["stepinterval"])
            values = []

            curval = minstep
            while curval <= maxstep:  # includes maxstep
                values.append(round(curval, 2))
                curval = curval + step

            # Current scenes times number of new values
            # 3 original runs (1 2 3), this settings adds two (a b) thus we now
            # have 6 scenes ( 1 1 2 2 3 3).
            self.parameters = [
                copy.copy(p) for p in
                self.parameters for _ in range(len(values))
            ]

            i = 0
            for scene in self.parameters:
                s = dict(setting)  # by using dict, we prevent an alias
                # Using modulo we can assign a b in the correct
                # way (1a 1b 2a 2b 3a 3b), because at index 2 (the first 2)
                # modulo gives 0 which is again the first value (a)
                s['value'] = values[i % len(values)]
                scene[key] = s
                i += 1

    def __unicode__(self):

        return self.name


# SCENE


class Scene(models.Model):

    """
    Scene model
    """

    name = models.CharField(max_length=256)
    suid = models.CharField(max_length=256, editable=False)

    scenario = models.ForeignKey('Scenario', null=True)

    fileurl = models.CharField(max_length=256)
    info = JSONField(blank=True)
    parameters = JSONField(blank=True)  # {"dt":20}
    state = models.CharField(max_length=256, blank=True)
    task_id = models.CharField(max_length=256)
    workingdir = models.CharField(max_length=256)

    # PROPERTY METHODS

    def get_absolute_url(self):

        return "{0}?id={1}".format(reverse_lazy('scene_detail'), self.id)

    def serialize(self):

        self._update_state()

        return {
            "id": self.id,
            "info": self.info,
            "name": self.name,
            "suid": self.suid,
            "workingdir": self.workingdir,
            "state": self.state,
            "fileurl": self.fileurl,
            "scenario": self.scenario.id if self.scenario else None
        }

    # CONTROL METHODS

    def start(self):

        result = AbortableAsyncResult(self.task_id)

        if self.task_id != "" and result.state == "PENDING":
            return {"error": "task already PENDING", "task_id": self.task_id}
        if result.state == BUSYSTATE:
            return {"error": "task already busy", "task_id": self.task_id}

        result = chainedtask.delay(self.parameters, self.workingdir)
        self.task_id = result.task_id
        self.state = result.state
        self.save()

        return {"task_id": self.task_id, "scene_id": self.suid}

    def update_state(self):
        # only update state if it has a task_id (which means the task is
        # started)
        if self.task_id != '':
            result = AbortableAsyncResult(self.task_id)
            self.info = result.info if isinstance(
                result.info, dict) else {"info": str(result.info)}
            self.state = result.state
            self.save()
        return {
            "task_id": self.task_id,
            "state": self.state,
            "info": str(self.info)
        }

    def save(self, *args, **kwargs):
        # if scene does not have a unique uuid, create it and create folder
        if self.suid == '':
            self.suid = str(uuid.uuid4())
            self.workingdir = os.path.join(
                settings.WORKER_FILEDIR, self.suid, '')
            # self._create_datafolder()
            if self.parameters == "":
                # Hack to have the "dt:20" in the correct format
                # when a scene has been created manually
                self.parameters = {"delft3d": self.info}
            # self._create_ini()
            self.fileurl = os.path.join(settings.WORKER_FILEURL, self.suid, '')
        super(Scene, self).save(*args, **kwargs)

    def abort(self):

        result = AbortableAsyncResult(self.task_id)
        self.info = result.info if isinstance(
            result.info, dict) else {"info": str(result.info)}
        if not result.state == BUSYSTATE:
            return {
                "error": "task is not busy",
                "task_id": self.task_id,
                "state": result.state,
                "info": str(self.info)
            }

        result.abort()

        self.info = result.info if isinstance(
            result.info, dict) else {"info": str(result.info)}
        self.state = result.state
        self.save()

        return {
            "task_id": self.task_id,
            "state": result.state,
            "info": str(self.info)
        }

    def revoke(self):

        result = AbortableAsyncResult(self.task_id)
        self.info = result.info if isinstance(
            result.info, dict) else {"info": str(result.info)}
        revoke_task(self.task_id, terminate=False)  # thou shalt not terminate
        self.state = result.state
        self.save()

        return {
            "task_id": self.task_id,
            "state": result.state,
            "info": str(self.info)
        }

    def delete(self, deletefiles=False, *args, **kwargs):
        self.abort()
        if deletefiles:
            self._delete_datafolder()
        super(Scene, self).delete(*args, **kwargs)

    def _create_datafolder(self):
        # create directory for scene
        # if not os.path.exists(self.workingdir):
            # os.makedirs(self.workingdir, 2775)
        pass

    def _delete_datafolder(self):
        # delete directory for scene
        if os.path.exists(self.workingdir):
            try:
                os.rmtree(self.workingdir)
            except:
                # Files written by root can't be deleted by django
                logging.error("Failed to delete working directory")

    def _create_ini(self):
        # create ini file for containers
        # in 2.7 ConfigParser is a bit stupid
        # in 3.x configparser has .read_dict()
        # config = ConfigParser.SafeConfigParser()
        # for section in self.parameters:
        #     if not config.has_section(section):
        #         config.add_section(section)
        #     for key, value in self.parameters[section].items():
        #         if not config.has_option(section, key):
        #             config.set(*map(str, [section, key, value]))

        # with open(os.path.join(self.workingdir, 'input.ini'), 'w') as f:
        #     config.write(f)  # Yes, the ConfigParser writes to f
        pass

    def export(self):

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
                if ext in ('.png', '.jpg', '.gif'):
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, self.workingdir)
                    zf.write(abs_path, rel_path)

        # Must close zip for all contents to be written
        zf.close()
        return stream, zip_filename

    # CRUD METHODS

    def save(self, *args, **kwargs):

        # if scene does not have a unique uuid, create it and create folder
        if self.suid == '':
            self.suid = str(uuid.uuid4())
            self.workingdir = os.path.join(
                settings.WORKER_FILEDIR, self.suid, '')
            self._create_datafolder()
            if self.parameters == "":
                # Hack to have the "dt:20" in the correct format
                self.parameters = {"delft3d": self.info}
            self._create_ini()
            self.fileurl = os.path.join(settings.WORKER_FILEURL, self.suid, '')
        super(Scene, self).save(*args, **kwargs)

    def delete(self, deletefiles=False, *args, **kwargs):

        self.abort()
        if deletefiles:
            self._delete_datafolder()
        super(Scene, self).delete(*args, **kwargs)

    # INTERNALS

    def _create_datafolder(self):

        # create directory for scene
        if not os.path.exists(self.workingdir):
            os.makedirs(self.workingdir)

    def _delete_datafolder(self):

        # delete directory for scene
        if os.path.exists(self.workingdir):
            rmtree(self.workingdir)

    def _create_ini(self):

        # create ini file for containers
        # in 2.7 ConfigParser is a bit stupid
        # in 3.x configparser has .read_dict()
        config = ConfigParser.SafeConfigParser()
        for section in self.parameters:
            if not config.has_section(section):
                config.add_section(section)
            for key, value in self.parameters[section].items():
                if not config.has_option(section, key):
                    config.set(*map(str, [section, key, value]))

        with open(os.path.join(self.workingdir, 'input.ini'), 'w') as f:
            config.write(f)  # Yes, the ConfigParser writes to f

    def _update_state(self):

        # only update state if it has a task_id (which means the task is
        # started)
        if self.task_id != '':
            result = AbortableAsyncResult(self.task_id)
            self.info = result.info if isinstance(
                result.info, dict) else {"info": str(result.info)}
            self.state = result.state

        self.info["delta_fringe_images"] = {
            "images": [],
            "location": ""
        }
        self.info["channel_network_images"] = {
            "images": [],
            "location": ""
        }
        self.info["logfile"] = ""
        for root, dirs, files in os.walk(self.workingdir):
            for f in sorted(files):
                name, ext = os.path.splitext(f)
                if ext in ('.png', '.jpg', '.gif'):
                    self.info["delta_fringe_images"]["images"].append(f)
                    self.info["channel_network_images"]["images"].append(f)
                if ext == '.log':
                    self.info["logfile"] = f

        self.save()

    def __unicode__(self):
        return self.name


# ################################### Template

class Template(models.Model):

    """
    Template model
    """

    templatename = models.CharField(max_length=256)

    description = models.CharField(max_length=256, blank=True)
    email = models.CharField(max_length=256, blank=True)
    groups = JSONField(blank=True)
    label = models.CharField(max_length=256, blank=True)
    model = models.CharField(max_length=256, blank=True)
    site = models.CharField(max_length=256, blank=True)
    variables = JSONField(blank=True)
    version = models.IntegerField(blank=True)

    def get_absolute_url(self):
        return "{0}?id={1}".format(reverse_lazy('template_detail'), self.id)

    def __unicode__(self):
        return self.templatename
