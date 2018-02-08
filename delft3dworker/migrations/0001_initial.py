# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import delft3dworker.models
import jsonfield.fields
import django.utils.timezone
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Container',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('task_uuid', models.UUIDField(default=None, null=True, blank=True)),
                ('task_starttime', models.DateTimeField(default=django.utils.timezone.now, blank=True)),
                ('container_type', models.CharField(default=b'preprocess', max_length=16, choices=[(b'preprocess', b'preprocess'), (b'delft3d', b'delft3d'), (b'process', b'process'), (b'postprocess', b'postprocess'), (b'export', b'export'), (b'sync_cleanup', b'sync_cleanup'), (b'sync_rerun', b'sync_rerun')])),
                ('desired_state', models.CharField(default=b'non-existent', max_length=16, choices=[(b'non-existent', b'non-existent'), (b'created', b'created'), (b'restarting', b'restarting'), (b'running', b'running'), (b'paused', b'paused'), (b'exited', b'exited'), (b'dead', b'dead'), (b'unknown', b'unknown')])),
                ('docker_state', models.CharField(default=b'non-existent', max_length=16, choices=[(b'non-existent', b'non-existent'), (b'created', b'created'), (b'restarting', b'restarting'), (b'running', b'running'), (b'paused', b'paused'), (b'exited', b'exited'), (b'dead', b'dead'), (b'unknown', b'unknown')])),
                ('docker_id', models.CharField(default=b'', max_length=64, db_index=True, blank=True)),
                ('container_starttime', models.DateTimeField(default=django.utils.timezone.now, blank=True)),
                ('container_stoptime', models.DateTimeField(default=django.utils.timezone.now, blank=True)),
                ('container_exitcode', models.PositiveSmallIntegerField(default=0)),
                ('container_progress', models.PositiveSmallIntegerField(default=0)),
                ('docker_log', models.TextField(default=b'', blank=True)),
                ('container_log', models.TextField(default=b'', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Scenario',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('scenes_parameters', jsonfield.fields.JSONField(default=dict, blank=True)),
                ('parameters', jsonfield.fields.JSONField(default=dict, blank=True)),
                ('state', models.CharField(default=b'CREATED', max_length=64)),
                ('progress', models.IntegerField(default=0)),
                ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
            ],
            options={
                'permissions': (('view_scenario', 'View Scenario'),),
            },
        ),
        migrations.CreateModel(
            name='Scene',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('suid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, blank=True)),
                ('date_started', models.DateTimeField(null=True, blank=True)),
                ('fileurl', models.CharField(max_length=256)),
                ('info', jsonfield.fields.JSONField(default=dict, blank=True)),
                ('parameters', jsonfield.fields.JSONField(default=dict, blank=True)),
                ('state', models.CharField(default=b'CREATED', max_length=256)),
                ('progress', models.IntegerField(default=0)),
                ('task_id', models.CharField(max_length=256, blank=True)),
                ('workingdir', models.CharField(max_length=256)),
                ('parameters_hash', models.CharField(max_length=64, blank=True)),
                ('shared', models.CharField(max_length=1, choices=[(b'p', b'private'), (b'c', b'company'), (b'w', b'world')])),
                ('workflow', models.PositiveSmallIntegerField(default=0, choices=[(0, b'main workflow'), (1, b'redo processing workflow'), (2, b'redo postprocessing workflow'), (3, b'redo processing and postprocessing workflow')])),
                ('phase', models.PositiveSmallIntegerField(default=0, choices=[(0, b'New'), (2, b'Allocating preprocessing resources'), (3, b'Starting preprocessing'), (4, b'Running preprocessing'), (5, b'Finished preprocessing'), (6, b'Idle: waiting for user input'), (10, b'Allocating simulation resources'), (11, b'Starting simulation'), (12, b'Running simulation'), (15, b'Finishing simulation'), (13, b'Finished simulation'), (14, b'Stopping simulation'), (60, b'Allocating processing resources'), (61, b'Starting processing'), (62, b'Running processing'), (63, b'Finished processing'), (20, b'Allocating postprocessing resources'), (21, b'Starting postprocessing'), (22, b'Running postprocessing'), (23, b'Finished postprocessing'), (30, b'Allocating export resources'), (31, b'Starting export'), (32, b'Running export'), (33, b'Finished export'), (17, b'Starting container remove'), (18, b'Removing containers'), (19, b'Containers removed'), (40, b'Allocating synchronization resources'), (41, b'Started synchronization'), (42, b'Running synchronization'), (43, b'Finished synchronization'), (50, b'Allocating synchronization resources'), (51, b'Started synchronization'), (52, b'Running synchronization'), (53, b'Finished synchronization'), (500, b'Finished'), (1000, b'Starting Abort'), (1001, b'Aborting'), (1002, b'Finished Abort'), (1003, b'Queued')])),
                ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
                ('scenario', models.ManyToManyField(to='delft3dworker.Scenario', blank=True)),
            ],
            options={
                'permissions': (('view_scene', 'View Scene'),),
            },
        ),
        migrations.CreateModel(
            name='SearchForm',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('templates', jsonfield.fields.JSONField(default=b'[]')),
                ('sections', jsonfield.fields.JSONField(default=b'[]')),
            ],
        ),
        migrations.CreateModel(
            name='Template',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('meta', jsonfield.fields.JSONField(default=dict, blank=True)),
                ('sections', jsonfield.fields.JSONField(default=dict, blank=True)),
            ],
            options={
                'permissions': (('view_template', 'View Template'),),
            },
        ),
        migrations.CreateModel(
            name='Version_SVN',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('release', models.CharField(max_length=256, db_index=True)),
                ('revision', models.PositiveSmallIntegerField(db_index=True)),
                ('versions', jsonfield.fields.JSONField(default=b'{}')),
                ('url', models.URLField()),
                ('changelog', models.CharField(max_length=256)),
                ('reviewed', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['-revision'],
                'verbose_name': 'SVN version',
                'verbose_name_plural': 'SVN versions',
            },
        ),
        migrations.AddField(
            model_name='scene',
            name='version',
            field=models.ForeignKey(default=delft3dworker.models.default_svn_version, to='delft3dworker.Version_SVN', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='scenario',
            name='template',
            field=models.ForeignKey(blank=True, to='delft3dworker.Template', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='container',
            name='scene',
            field=models.ForeignKey(to='delft3dworker.Scene', on_delete=models.CASCADE),
        ),
    ]
