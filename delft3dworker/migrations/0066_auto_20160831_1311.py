# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0065_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scene',
            name='phase',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, 'New'), (1, 'Creating containers...'), (2, 'Created containers'), (3, 'Starting preprocessing...'), (4, 'Running preprocessing...'), (5, 'Finished preprocessing'), (6, 'Idle: waiting for user input'), (7, 'Starting simulation...'), (8, 'Running simulation...'), (9, 'Finished simulation'), (10, 'Starting postprocessing...'), (11, 'Running postprocessing...'), (12, 'Finished postprocessing'), (13, 'Starting container remove...'), (14, 'Removing containers...'), (15, 'Containers removed'), (1000, 'Starting Abort...'), (1001, 'Aborting...'), (1002, 'Finished Abort')]),
        ),
    ]
