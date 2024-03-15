# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0082_auto_20161122_1530"),
    ]

    operations = [
        migrations.AddField(
            model_name="scene",
            name="workflow",
            field=models.PositiveSmallIntegerField(
                default=0,
                choices=[
                    (0, "main workflow"),
                    (1, "redo processing workflow"),
                    (2, "redo postprocessing workflow"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="container",
            name="container_type",
            field=models.CharField(
                default="preprocess",
                max_length=16,
                choices=[
                    ("preprocess", "preprocess"),
                    ("delft3d", "delft3d"),
                    ("process", "process"),
                    ("postprocess", "postprocess"),
                    ("export", "export"),
                    ("sync_cleanup", "sync_cleanup"),
                    ("sync_rerun", "sync_rerun"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="scene",
            name="phase",
            field=models.PositiveSmallIntegerField(
                default=0,
                choices=[
                    (0, "New"),
                    (2, "Allocating preprocessing resources"),
                    (3, "Starting preprocessing"),
                    (4, "Running preprocessing"),
                    (5, "Finished preprocessing"),
                    (6, "Idle: waiting for user input"),
                    (10, "Allocating simulation resources"),
                    (11, "Starting simulation"),
                    (12, "Running simulation"),
                    (15, "Finishing simulation"),
                    (13, "Finished simulation"),
                    (14, "Stopping simulation"),
                    (60, "Allocating processing resources"),
                    (61, "Starting processing"),
                    (62, "Running processing"),
                    (63, "Finished processing"),
                    (20, "Allocating postprocessing resources"),
                    (21, "Starting postprocessing"),
                    (22, "Running postprocessing"),
                    (23, "Finished postprocessing"),
                    (30, "Allocating export resources"),
                    (31, "Starting export"),
                    (32, "Running export"),
                    (33, "Finished export"),
                    (17, "Starting container remove"),
                    (18, "Removing containers"),
                    (19, "Containers removed"),
                    (40, "Allocating synchronization resources"),
                    (41, "Started synchronization"),
                    (42, "Running synchronization"),
                    (43, "Finished synchronization"),
                    (50, "Allocating synchronization resources"),
                    (51, "Started synchronization"),
                    (52, "Running synchronization"),
                    (53, "Finished synchronization"),
                    (500, "Finished"),
                    (1000, "Starting Abort"),
                    (1001, "Aborting"),
                    (1002, "Finished Abort"),
                    (1003, "Queued"),
                ],
            ),
        ),
    ]
