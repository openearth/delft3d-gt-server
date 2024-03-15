# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0077_auto_20161018_0925"),
    ]

    operations = [
        migrations.AddField(
            model_name="scene",
            name="date_created",
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
        migrations.AddField(
            model_name="scene",
            name="date_started",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
