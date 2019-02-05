# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0048_container_scene'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='desired_state',
            field=models.CharField(default='non-existent', max_length=16, choices=[('non-existent', 'non-existent'), ('created', 'created'), ('restarting', 'restarting'), ('running', 'running'), ('paused', 'paused'), ('exited', 'exited'), ('dead', 'dead')]),
        ),
        migrations.AlterField(
            model_name='container',
            name='docker_state',
            field=models.CharField(default='non-existent', max_length=16, choices=[('non-existent', 'non-existent'), ('created', 'created'), ('restarting', 'restarting'), ('running', 'running'), ('paused', 'paused'), ('exited', 'exited'), ('dead', 'dead')]),
        ),
    ]
