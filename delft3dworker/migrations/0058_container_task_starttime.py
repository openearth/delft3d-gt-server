# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0057_auto_20160829_1429"),
    ]

    operations = [
        migrations.AddField(
            model_name="container",
            name="task_starttime",
            field=models.DateTimeField(
                default=datetime.datetime(2016, 8, 30, 9, 36, 4, 550600, tzinfo=utc),
                blank=True,
            ),
        ),
    ]
