# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0058_container_task_starttime"),
    ]

    operations = [
        migrations.AddField(
            model_name="container",
            name="container_starttime",
            field=models.DateTimeField(
                default=datetime.datetime(
                    2016, 8, 30, 10, 42, 12, 820124, tzinfo=datetime.timezone.utc
                ),
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name="container",
            name="container_stoptime",
            field=models.DateTimeField(
                default=datetime.datetime(
                    2016, 8, 30, 10, 42, 12, 820153, tzinfo=datetime.timezone.utc
                ),
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="container",
            name="task_starttime",
            field=models.DateTimeField(
                default=datetime.datetime(
                    2016, 8, 30, 10, 42, 12, 820170, tzinfo=datetime.timezone.utc
                ),
                blank=True,
            ),
        ),
    ]
