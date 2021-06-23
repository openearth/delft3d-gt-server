# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0067_container_container_exitcode"),
    ]

    operations = [
        migrations.AddField(
            model_name="container",
            name="container_progress",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
