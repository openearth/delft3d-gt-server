# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0034_scene_shared'),
    ]

    operations = [
        migrations.AddField(
            model_name='scene',
            name='parameters_hash',
            field=models.CharField(unique=True, max_length=64, blank=True),
        ),
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
