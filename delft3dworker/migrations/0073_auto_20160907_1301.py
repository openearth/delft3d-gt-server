# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0072_auto_20160830_2334"),
    ]

    operations = [
        migrations.AlterField(
            model_name="container",
            name="container_type",
            field=models.CharField(
                default="preprocess",
                max_length=16,
                choices=[
                    ("preprocess", "preprocess"),
                    ("delft3d", "delft3d"),
                    ("process", "process"),
                    ("postprocess", "postprocess"),
                    ("export", "export"),
                    ("sync_cleanup", "sync_cleanup"),
                ],
            ),
        ),
    ]
