from django.db import models  #noqa


class Delft3DWorker(models.Model):
	name = models.CharField(max_length=256)
	uuid = models.CharField(max_length=256)
	status = models.CharField(max_length=256)
	progress = models.IntegerField()
	timeleft = models.IntegerField()
