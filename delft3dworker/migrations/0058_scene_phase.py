# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0057_auto_20160829_1429'),
    ]

    operations = [
        migrations.AddField(
            model_name='scene',
            name='phase',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'Phase 0'), (1, b'Phase 1'), (2, b'Phase 2'), (3, b'Phase 3'), (4, b'Phase 4'), (5, b'Phase 5'), (6, b'Phase 6'), (7, b'Phase 7')]),
        ),
    ]
