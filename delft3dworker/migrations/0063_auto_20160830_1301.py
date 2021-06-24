# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0062_auto_20160830_1300"),
    ]

    operations = [
        migrations.AlterField(
            model_name="container",
            name="task_starttime",
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
    ]
