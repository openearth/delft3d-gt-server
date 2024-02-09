# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0060_auto_20160830_1258"),
    ]

    operations = [
        migrations.AlterField(
            model_name="container",
            name="task_starttime",
            field=models.DateTimeField(
                default=datetime.datetime(
                    2016, 8, 30, 13, 0, 33, 231999, tzinfo=datetime.timezone.utc
                ),
                blank=True,
            ),
        ),
    ]
