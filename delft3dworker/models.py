import os

from shutil import copytree, copystat, rmtree
from datetime import datetime

from django.conf import settings  #noqa
from django.db import models  #noqa
from jsonfield import JSONField

from mako.template import Template


class Delft3DWorker(models.Model):
    uuid = models.CharField(max_length=256, editable=False)
    workerid = models.CharField(max_length=256, editable=False)
    workingdir = models.CharField(max_length=256, editable=False)
    fileurl = models.CharField(max_length=256, editable=False)

    name = models.CharField(max_length=256)
    status = models.CharField(max_length=256)
    info = models.CharField(max_length=256)
    json = JSONField()

    def save(self, *args, **kwargs):
        self.workingdir = "{0}/{1}/".format(settings.WORKER_FILEDIR, self.uuid)
        self.fileurl = "{0}/{1}/".format(settings.WORKER_FILEURL, self.uuid)
        self._create_model_schema()
        super(Delft3DWorker, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):

        if os.path.exists(self.workingdir):
            rmtree(self.workingdir)
        
        super(Delft3DWorker, self).delete(*args, **kwargs)

    def __unicode__(self):
        
        return "{0} - {1}".format(self.name, self.uuid)

    def _create_model_schema(self):
        
        if not os.path.exists(self.workingdir):
            copytree('/data/container/delft3ddefaults', self.workingdir)

        # create input dict for template renderer
        time_format = "%Y-%m-%d %H:%M:%S"
        input_dict =   {
            "discharge": 1250,
            "dt": self.json["dt"],
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
        with open(os.path.join(self.workingdir, 'a.mdf'), 'w') as output:
            output.write(rendered_schema)
