# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0059_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='task_starttime',
            field=models.DateTimeField(default=datetime.datetime(2016, 8, 30, 12, 58, 18, 702032, tzinfo=utc), blank=True),
        ),
        migrations.AlterField(
            model_name='scene',
            name='phase',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'New'), (1, b'Creating containers...'), (2, b'Created containers'), (3, b'Starting preprocessing...'), (4, b'Running preprocessing...'), (5, b'Finished preprocessing'), (6, b'Idle'), (7, b'Starting simulation...'), (8, b'Running simulation...'), (9, b'Finished simulation'), (10, b'Starting postprocessing...'), (11, b'Running postprocessing...'), (12, b'Finished postprocessing'), (13, b'Starting container remove...'), (14, b'Removing containers...'), (15, b'Containers removed'), (1000, b'Starting Abort...'), (1001, b'Aborting...'), (1002, b'Finished Abort')]),
        ),
    ]
