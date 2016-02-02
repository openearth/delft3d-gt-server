import os

from shutil import copytree, rmtree

from django.conf import settings  #noqa
from django.db import models  #noqa
from jsonfield import JSONField


class Delft3DWorker(models.Model):
    uuid = models.CharField(max_length=256, editable=False)
    workingdir = models.CharField(max_length=256, editable=False)

    name = models.CharField(max_length=256)
    status = models.CharField(max_length=256)
    progress = models.IntegerField()
    timeleft = models.IntegerField()
    json = JSONField()

    def save(self, *args, **kwargs):
        
        workingdir = "{0}/{1}".format(settings.WORKER_FILEDIR, self.uuid)
        if not os.path.exists(workingdir):
            os.makedirs(workingdir)
        self.workingdir = workingdir

        self._create_model_schema()

        super(Delft3DWorker, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if os.path.exists(self.workingdir):
            rmtree(self.workingdir)
        super(Delft3DWorker, self).delete(*args, **kwargs)

    def _create_model_schema(self):
        # TODO: replace this with actual schema creation
        rmtree(self.workingdir)
        copytree('/data/container/01_standard'.format(self.workingdir), self.workingdir)
        # TODO END

    def __unicode__(self):
        return "{0} - {1}".format(self.name, self.uuid)
