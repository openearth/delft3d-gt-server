# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0057_auto_20160829_1429"),
    ]

    operations = [
        migrations.AddField(
            model_name="scene",
            name="phase",
            field=models.PositiveSmallIntegerField(
                default=0,
                choices=[
                    (0, "Phase 0"),
                    (1, "Phase 1"),
                    (2, "Phase 2"),
                    (3, "Phase 3"),
                    (4, "Phase 4"),
                    (5, "Phase 5"),
                    (6, "Phase 6"),
                    (7, "Phase 7"),
                ],
            ),
        ),
    ]
