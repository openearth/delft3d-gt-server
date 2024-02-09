# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0070_auto_20160901_0755"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scene",
            name="phase",
            field=models.PositiveSmallIntegerField(
                default=0,
                choices=[
                    (0, "New"),
                    (1, "Creating containers..."),
                    (2, "Created containers"),
                    (3, "Starting preprocessing..."),
                    (4, "Running preprocessing..."),
                    (5, "Finished preprocessing"),
                    (6, "Idle: waiting for user input"),
                    (7, "Starting simulation..."),
                    (8, "Running simulation..."),
                    (9, "Finished simulation"),
                    (10, "Stopping simulation..."),
                    (11, "Starting postprocessing..."),
                    (12, "Running postprocessing..."),
                    (13, "Finished postprocessing"),
                    (14, "Starting export..."),
                    (15, "Running export..."),
                    (16, "Finished export"),
                    (17, "Starting container remove..."),
                    (18, "Removing containers..."),
                    (19, "Containers removed"),
                    (1000, "Starting Abort..."),
                    (1001, "Aborting..."),
                    (1002, "Finished Abort"),
                    (1003, "Queued"),
                ],
            ),
        ),
    ]
