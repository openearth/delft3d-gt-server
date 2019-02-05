# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0046_auto_20160715_1022'),
    ]

    operations = [
        migrations.CreateModel(
            name='Container',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('docker_id', models.CharField(unique=True, max_length=64, blank=True)),
                ('container_type', models.CharField(blank=True, max_length=16, choices=[('preprocess', 'preprocess'), ('delft3d', 'delft3d'), ('process', 'process'), ('postprocess', 'postprocess'), ('export', 'export')])),
                ('desired_state', models.CharField(blank=True, max_length=16, choices=[('non-existent', 'non-existent'), ('created', 'created'), ('running', 'running'), ('exited', 'exited')])),
                ('docker_state', models.CharField(blank=True, max_length=16, choices=[('non-existent', 'non-existent'), ('created', 'created'), ('running', 'running'), ('exited', 'exited')])),
            ],
        ),
    ]
