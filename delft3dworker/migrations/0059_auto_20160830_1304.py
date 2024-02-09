# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0058_container_task_starttime"),
    ]

    operations = [
        migrations.AlterField(
            model_name="container",
            name="task_starttime",
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
    ]
