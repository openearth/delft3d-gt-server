from django.db import models  #noqa
from jsonfield import JSONField


class Delft3DWorker(models.Model):
	name = models.CharField(max_length=256)
	uuid = models.CharField(max_length=256)
	status = models.CharField(max_length=256)
	progress = models.IntegerField()
	timeleft = models.IntegerField()
	json = JSONField()

	# def createModelSchema(self):

