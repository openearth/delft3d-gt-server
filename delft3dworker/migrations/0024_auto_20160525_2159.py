# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0023_scene_parameters_hash'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scene',
            name='scenario',
        ),
        migrations.AddField(
            model_name='scene',
            name='scenario',
            field=models.ManyToManyField(to='delft3dworker.Scenario', null=True),
        ),
    ]
