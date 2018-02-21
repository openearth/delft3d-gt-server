# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0069_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scene',
            name='phase',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'New'), (1, b'Creating containers...'), (2, b'Created containers'), (3, b'Starting preprocessing...'), (4, b'Running preprocessing...'), (5, b'Finished preprocessing'), (6, b'Idle: waiting for user input'), (7, b'Starting simulation...'), (8, b'Running simulation...'), (9, b'Finished simulation'), (10, b'Stopping simulation...'), (11, b'Starting postprocessing...'), (12, b'Running postprocessing...'), (13, b'Finished postprocessing'), (14, b'Starting export...'), (15, b'Running export...'), (16, b'Finished export'), (17, b'Starting container remove...'), (18, b'Removing containers...'), (19, b'Containers removed'), (1000, b'Starting Abort...'), (1001, b'Aborting...'), (1002, b'Finished Abort')]),
        ),
    ]
