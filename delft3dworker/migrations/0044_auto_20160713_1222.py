# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0043_scene_suid'),
    ]

    operations = [
        migrations.AddField(
            model_name='scenario',
            name='progress',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='scenario',
            name='state',
            field=models.CharField(max_length=64, blank=True),
        ),
        migrations.AddField(
            model_name='scene',
            name='progress',
            field=models.IntegerField(default=0),
        ),
    ]
