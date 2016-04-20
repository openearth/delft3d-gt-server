from __future__ import absolute_import

import os
import uuid
import json

from celery.contrib.abortable import AbortableAsyncResult
from celery.result import AsyncResult
from celery.exceptions import TimeoutError
from celery.task.control import revoke as revoke_task

from datetime import datetime

from delft3dworker.tasks import chainedtask

from django.conf import settings  #noqa
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
    template = models.OneToOneField('Template')

    name = models.CharField(max_length=256)
    parameters = JSONField(blank=True)

    def start(self):
        return "started"

    def get_absolute_url(self):
        return "{0}?id={1}".format(reverse_lazy('scenario_detail'), self.id)

    def __unicode__(self):
        return self.name


# ################################### SCENE


class Scene(models.Model):
    """
    Scene model
    """
    scenario = models.ForeignKey('Scenario')

    suid = models.CharField(max_length=256, editable=False)

    workingdir = models.CharField(max_length=256)
    fileurl = models.CharField(max_length=256)

    name = models.CharField(max_length=256)
    state = models.CharField(max_length=256, blank=True)
    info = JSONField(blank=True)
    parameters = JSONField(blank=True)  # {"dt":20}

    # Celery task
    task_id = models.CharField(max_length=256)
    state = models.CharField(max_length=256, blank=True)

    def start(self):
        result = AbortableAsyncResult(self.task_id)

        if self.task_id != "" and result.state == "PENDING":
            return {"error": "task already PENDING", "task_id": self.task_id}
        if result.state == BUSYSTATE:
            return {"error": "task already busy", "task_id": self.task_id}

        result = chainedtask.delay(10, self.workingdir)
        self.task_id = result.task_id
        self.state = result.state
        self.save()

        return {"task_id": self.task_id, "scene_id": self.suid}

    def update_state(self):
        result = AbortableAsyncResult(self.task_id)
        self.info = result.info if isinstance(result.info, dict) else {"info": result.info}
        self.state = result.state
        self.save()
        return {"task_id": self.task_id, "state": self.state, "info": self.info}

    def save(self, *args, **kwargs):
        if self.suid == '':
            self.suid = str(uuid.uuid4())
            self.workingdir = os.path.join(settings.WORKER_FILEDIR, self.suid, '')
            self._create_datafolder()
            self.fileurl = os.path.join(settings.WORKER_FILEURL, self.suid, '')
        super(Scene, self).save(*args, **kwargs)

    def abort(self):
        result = AbortableAsyncResult(self.task_id)
        self.info = result.info if isinstance(result.info, dict) else {"info": result.info}
        if not result.state == BUSYSTATE:
            return {"error": "task is not busy", "task_id": self.task_id, "state": result.state, "info": self.info}

        result.abort()

        self.info = result.info if isinstance(result.info, dict) else {"info": result.info}
        self.state = result.state
        self.save()

        return {"task_id": self.task_id, "state": result.state, "info": self.info}

    # Function is not used now
    def revoke(self):
        result = AbortableAsyncResult(self.task_id)
        self.info = result.info if isinstance(result.info, dict) else {"info": result.info}
        revoke_task(self.task_id, terminate=False)  # thou shalt not terminate
        self.state = result.state
        self.save()

        return {"task_id": self.task_id, "state": result.state, "info": self.info}

    def delete(self, *args, **kwargs):
        self.abort()
        super(Scene, self).delete(*args, **kwargs)

    def _create_datafolder(self):
        # create directory for scene
        if not os.path.exists(self.workingdir):
            os.makedirs(self.workingdir)

    def get_absolute_url(self):
        return "{0}?id={1}".format(reverse_lazy('scene_detail'), self.id)

    def __unicode__(self):
        return self.name


# ################################### TASKS
# ALL TASKS ARE DEPRECATED
# ### Superclass

class CeleryTask(models.Model):
    """
    Celery Task model
    """
    uuid = models.CharField(max_length=256)
    state = models.CharField(max_length=256, blank=True)
    state_meta = JSONField(blank=True)

    def result(self):
        return AsyncResult(self.uuid)

    def serialize(self):
        # update state
        result = AsyncResult(self.uuid)
        self.state = result.state

        # dictify info if not a dict (e.g. in case of an error)
        if type(result.info) is dict:
            self.state_meta = result.info
        else:
            self.state_meta = {'info': {"info":result.info}}

        self.save()

        return {
            'uuid': self.uuid,
            'state': self.state,
            'state_meta': self.state_meta,
        }

    def run(self):
        result = donothing.delay()


        self.uuid = result.task_id
        self.state = result.state
        self.state_meta = result.info or {}
        self.save()

    def delete(self, *args, **kwargs):
        result = AbortableAsyncResult(self.uuid)
        print result.info
        print "Deleting Celery Task {}".format(self.uuid)
        result.abort()
        print result.is_aborted()
        # result.get()
        super(CeleryTask, self).delete(*args, **kwargs)

    def __unicode__(self):
        return "{0} - {1}".format(self.uuid, self.state)


# ### Subclasses

class PostprocessingTask(CeleryTask):
    """
    Postprocessing task model
    """
    scene = models.ForeignKey('Scene')

    def run(self):
        result = postprocess.delay()
        self.uuid = result.task_id
        self.state = result.state
        self.state_meta = result.info or {}
        self.save()

    def __unicode__(self):
        return "{0} - {1} - {2}".format(self.scene, self.uuid, self.state)


class ProcessingTask(CeleryTask):
    """
    Processing task model
    """
    scene = models.OneToOneField('Scene')

    def run(self):
        result = process.delay(self.scene.workingdir)
        self.uuid = result.task_id
        self.state = result.state
        self.state_meta = result.info or {}
        self.save()

        return True

    def abort(self):
        result = AbortableAsyncResult(self.uuid)
        result.abort()

    def delete(self, *args, **kwargs):
        result = AbortableAsyncResult(self.uuid)
        print result.info
        print "Deleting ProcessingTask {}".format(self.uuid)
        result.abort()
        print result.is_aborted()
        print result.state
        # result.get()  # will hang
        super(ProcessingTask, self).delete(*args, **kwargs)

    def __unicode__(self):
        return "{0} - {1} - {2}".format(self.scene, self.uuid, self.state)


class SimulationTask(CeleryTask):
    """
    Simulation task model
    """
    scene = models.OneToOneField('Scene')

    def run(self):

        # Prepare model input
        if not self._create_model_schema():
            return False

        result = simulate.delay(self.scene.workingdir)
        self.uuid = result.task_id
        self.state = result.state
        self.state_meta = result.info or {}
        self.save()
        return True

    def abort(self):
        result = AbortableAsyncResult(self.uuid)
        result.abort()

    def delete(self, *args, **kwargs):
        result = AbortableAsyncResult(self.uuid)
        print "Deleting SimulationTask {}".format(self.uuid)
        result.abort()
        print result.is_aborted()
        # result.get()  # will hang
        super(SimulationTask, self).delete(*args, **kwargs)

    # def after_return(self, *args, **kwargs):
    #     if self.state_meta == "Exited":
    #         self.update_state(state="FAILURE")
    #     super(SimulationTask, self).after_return(*args, **kwargs)

    def _create_model_schema(self):

        if not u'dt' in self.scene.info:
            return False

        # create directory for scene
        if not os.path.exists(self.scene.workingdir):
            copytree('/data/container/delft3ddefaults', os.path.join(self.scene.workingdir, 'delft3d'))

        # create input dict for template renderer
        time_format = "%Y-%m-%d %H:%M:%S"
        input_dict = {
            "discharge": 1250,
            "dt": self.scene.info['dt'],
            "his_interval": 120,
            "map_interval": 1440,
            "reference_time": "2013-12-01 00:00:00",
            "Tstart": "2014-01-01 00:00:00",
            "Tstop": "2015-01-01 00:00:00"
        }

        ref_time = datetime.strptime(input_dict['reference_time'], time_format)
        start_time = datetime.strptime(input_dict['Tstart'], time_format)
        stop_time = datetime.strptime(input_dict['Tstop'], time_format)

        input_dict['reference_time'] = datetime.strftime(ref_time, "%Y-%m-%d")
        input_dict['Tstart'] = (start_time - ref_time).total_seconds()/60
        input_dict['Tstop'] = (stop_time - ref_time).total_seconds()/60

        # render and write a.mdf
        mdf_template_file = os.path.join('/data/container/delft3dtemplates', 'a.mdf')
        mdf_template = MakoTemplate(filename=mdf_template_file)
        rendered_schema = mdf_template.render(**input_dict).replace('\r\n','\n')
        with open(os.path.join(self.scene.workingdir, 'delft3d', 'a.mdf'), 'w') as output:
            output.write(rendered_schema)

        return True

    def __unicode__(self):
        return "{0} - {1} - {2}".format(self.scene, self.uuid, self.state)


# ################################### Template

class Template(models.Model):
    """
    Template model
    """

    templatename = models.CharField(max_length=256)

    version  = models.IntegerField(max_length=256, blank=True)
    model = models.CharField(max_length=256, blank=True)
    email = models.CharField(max_length=256, blank=True)
    label = models.CharField(max_length=256, blank=True)
    description = models.CharField(max_length=256, blank=True)
    site = models.CharField(max_length=256, blank=True)
    groups = JSONField(blank=True)
    variables = JSONField(blank=True)

    def get_absolute_url(self):
        return "{0}?id={1}".format(reverse_lazy('template_detail'), self.id)

    def __unicode__(self):
        return self.templatename
