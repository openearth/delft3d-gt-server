# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0075_auto_20161012_1147'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scene',
            name='phase',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, 'New'), (2, 'Creating preprocessing'), (3, 'Starting preprocessing'), (4, 'Running preprocessing'), (5, 'Finished preprocessing'), (6, 'Idle: waiting for user input'), (10, 'Creating simulation'), (11, 'Starting simulation'), (12, 'Running simulation'), (13, 'Finished simulation'), (14, 'Stopping simulation'), (20, 'Creating postprocessing'), (21, 'Starting postprocessing'), (22, 'Running postprocessing'), (23, 'Finished postprocessing'), (30, 'Creating export'), (31, 'Starting export'), (32, 'Running export'), (33, 'Finished export'), (17, 'Starting container remove'), (18, 'Removing containers'), (19, 'Containers removed'), (40, 'Creating synchronization'), (41, 'Started synchronization'), (42, 'Running synchronization'), (43, 'Finished synchronization'), (50, 'Finished'), (1000, 'Starting Abort'), (1001, 'Aborting'), (1002, 'Finished Abort'), (1003, 'Queued')]),
        ),
    ]
