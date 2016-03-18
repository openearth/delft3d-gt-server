from __future__ import absolute_import

import os
import uuid

from celery.contrib.abortable import AbortableAsyncResult
from celery.result import AsyncResult

from datetime import datetime

from delft3dworker.tasks import donothing
from delft3dworker.tasks import postprocess
from delft3dworker.tasks import process
from delft3dworker.tasks import simulate

from django.conf import settings  #noqa
from django.core.urlresolvers import reverse_lazy
from django.db import models

from jsonfield import JSONField

from mako.template import Template

from shutil import copystat
from shutil import copytree
from shutil import rmtree


# ################################### SCENE

class Scene(models.Model):
    """
    Scene model
    """
    suid = models.CharField(max_length=256, editable=False)

    workingdir = models.CharField(max_length=256)
    fileurl = models.CharField(max_length=256)

    name = models.CharField(max_length=256)
    state = models.CharField(max_length=256, blank=True)
    info = JSONField(blank=True)

    def start(self):
        started = True

        try:
            self.simulationtask
        except SimulationTask.DoesNotExist, e:
            simulationtask = SimulationTask(uuid='none', state='none',
                scene=self)
            started = started and simulationtask.run()

        try:
            self.processingtask
        except ProcessingTask.DoesNotExist, e:
            processingtask = ProcessingTask(uuid='none', state='none',
                scene=self)
            started = started and processingtask.run()

        return 'started' if started else 'error'

    def update_state(self):
        try:
            simstate = self.simulationtask.state
        except SimulationTask.DoesNotExist, e:
            simstate = None
        try:
            procstate = self.processingtask.state
        except ProcessingTask.DoesNotExist, e:
            procstate = None

        self.state = "WAITING"
        if simstate == "PROCESSING" or procstate == "PROCESSING":
            self.state = "PROCESSING"
        if simstate == "SUCCESS" and procstate == "SUCCESS":
            self.state = "SUCCESS"
        self.save()

    def save(self, *args, **kwargs):
        if self.suid == '':
            self.suid = str(uuid.uuid4())
            self.workingdir = os.path.join(settings.WORKER_FILEDIR, self.suid, '')
            self.fileurl = os.path.join(settings.WORKER_FILEURL, self.suid, '')
        super(Scene, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return "{0}?id={1}".format(reverse_lazy('scene_detail'), self.id)

    def __unicode__(self):
        return self.name


# ################################### TASKS

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
            self.state_meta = {'info': str(result.info)}

        self.save()

        return {
            'uuid': self.uuid,
            'state': self.state,
            'state_meta': self.state_meta,
        }

    def run(self):
        result = donothing.delay()
        self.uuid = result.id
        self.state = result.state
        self.state_meta = result.info or {}
        self.save()

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
        self.uuid = result.id
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
        self.uuid = result.id
        self.state = result.state
        self.state_meta = result.info or {}
        self.save()

        return True

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
        self.uuid = result.id
        self.state = result.state
        self.state_meta = result.info or {}
        self.save()
        return True

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
        mdf_template = Template(filename=mdf_template_file)
        rendered_schema = mdf_template.render(**input_dict).replace('\r\n','\n')
        with open(os.path.join(self.scene.workingdir, 'delft3d', 'a.mdf'), 'w') as output:
            output.write(rendered_schema)

        return True

    def __unicode__(self):
        return "{0} - {1} - {2}".format(self.scene, self.uuid, self.state)
