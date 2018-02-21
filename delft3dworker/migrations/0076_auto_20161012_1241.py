# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0075_auto_20161012_1147'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scene',
            name='phase',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'New'), (2, b'Creating preprocessing'), (3, b'Starting preprocessing'), (4, b'Running preprocessing'), (5, b'Finished preprocessing'), (6, b'Idle: waiting for user input'), (10, b'Creating simulation'), (11, b'Starting simulation'), (12, b'Running simulation'), (13, b'Finished simulation'), (14, b'Stopping simulation'), (20, b'Creating postprocessing'), (21, b'Starting postprocessing'), (22, b'Running postprocessing'), (23, b'Finished postprocessing'), (30, b'Creating export'), (31, b'Starting export'), (32, b'Running export'), (33, b'Finished export'), (17, b'Starting container remove'), (18, b'Removing containers'), (19, b'Containers removed'), (40, b'Creating synchronization'), (41, b'Started synchronization'), (42, b'Running synchronization'), (43, b'Finished synchronization'), (50, b'Finished'), (1000, b'Starting Abort'), (1001, b'Aborting'), (1002, b'Finished Abort'), (1003, b'Queued')]),
        ),
    ]
