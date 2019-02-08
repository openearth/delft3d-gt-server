# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-05-29 09:42
from __future__ import unicode_literals

import delft3dworker.utils
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0087_auto_20180214_1324'),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, unique=True)),
                ('starttime', models.DateTimeField(blank=True, default=delft3dworker.utils.tz_now)),
                ('task_uuid', models.UUIDField(blank=True, default=None, null=True)),
                ('task_starttime', models.DateTimeField(blank=True, default=delft3dworker.utils.tz_now)),
                ('desired_state', models.CharField(choices=[('non-existent', 'Non-existent'), ('pending', 'Pending'), ('unknown', 'Unknown'), ('running', 'Running'), ('paused', 'Running (Suspended)'), ('succeeded', 'Succeeded'), ('skipped', 'Skipped'), ('failed', 'Failed'), ('error', 'Error')], default='non-existent', max_length=16)),
                ('cluster_state', models.CharField(choices=[('non-existent', 'Non-existent'), ('pending', 'Pending'), ('unknown', 'Unknown'), ('running', 'Running'), ('paused', 'Running (Suspended)'), ('succeeded', 'Succeeded'), ('skipped', 'Skipped'), ('failed', 'Failed'), ('error', 'Error')], default='non-existent', max_length=16)),
                ('progress', models.PositiveSmallIntegerField(default=0)),
            ],
        ),
        migrations.RemoveField(
            model_name='scene',
            name='workflow',
        ),
        migrations.AddField(
            model_name='scene',
            name='entrypoint',
            field=models.PositiveSmallIntegerField(choices=[(0, 'main workflow')], default=0),
        ),
        migrations.AddField(
            model_name='template',
            name='export_options',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}),
        ),
        migrations.AddField(
            model_name='template',
            name='info',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={'channel_network_images': {'images': [], 'location': 'process/'}, 'delta_fringe_images': {'images': [], 'location': 'process/'}, 'logfile': {'file': '', 'location': 'simulation/'}, 'postprocess_output': {}, 'procruns': 0, 'sediment_fraction_images': {'images': [], 'location': 'process/'}, 'subenvironment_images': {'images': [], 'location': 'postprocess/'}}),
        ),
        migrations.AddField(
            model_name='template',
            name='visualisation',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}),
        ),
        migrations.AddField(
            model_name='template',
            name='yaml_template',
            field=models.FileField(default='', upload_to='workflows/'),
        ),
        migrations.AlterField(
            model_name='scene',
            name='phase',
            field=models.PositiveSmallIntegerField(choices=[(0, 'New'), (6, 'Idle: waiting for user input'), (11, 'Starting workflow'), (12, 'Running workflow'), (13, 'Removing workflow'), (500, 'Finished')], default=0),
        ),
        migrations.AddField(
            model_name='workflow',
            name='scene',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='delft3dworker.Scene'),
        ),
    ]
