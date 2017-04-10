# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0082_auto_20161122_1530'),
    ]

    operations = [
        migrations.AddField(
            model_name='scene',
            name='workflow',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'main workflow'), (1, b'redo processing workflow'), (2, b'redo postprocessing workflow')]),
        ),
        migrations.AlterField(
            model_name='scene',
            name='phase',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'New'), (2, b'Allocating preprocessing resources'), (3, b'Starting preprocessing'), (4, b'Running preprocessing'), (5, b'Finished preprocessing'), (6, b'Idle: waiting for user input'), (10, b'Allocating simulation resources'), (11, b'Starting simulation'), (12, b'Running simulation'), (15, b'Finishing simulation'), (13, b'Finished simulation'), (14, b'Stopping simulation'), (60, b'Allocating processing resources'), (61, b'Starting processing'), (62, b'Running processing'), (63, b'Finished processing'), (20, b'Allocating postprocessing resources'), (21, b'Starting postprocessing'), (22, b'Running postprocessing'), (23, b'Finished postprocessing'), (30, b'Allocating export resources'), (31, b'Starting export'), (32, b'Running export'), (33, b'Finished export'), (17, b'Starting container remove'), (18, b'Removing containers'), (19, b'Containers removed'), (40, b'Allocating synchronization resources'), (41, b'Started synchronization'), (42, b'Running synchronization'), (43, b'Finished synchronization'), (50, b'Allocating synchronization resources'), (51, b'Started synchronization'), (52, b'Running synchronization'), (53, b'Finished synchronization'), (500, b'Finished'), (1000, b'Starting Abort'), (1001, b'Aborting'), (1002, b'Finished Abort'), (1003, b'Queued')]),
        ),
    ]
