# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0013_delete_delft3dworker"),
    ]

    operations = [
        migrations.AddField(
            model_name="scene",
            name="task_id",
            field=models.CharField(
                default="default value for backported scene", max_length=256
            ),
            preserve_default=False,
        ),
    ]
