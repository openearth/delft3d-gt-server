# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0033_merge"),
    ]

    operations = [
        migrations.AddField(
            model_name="scene",
            name="shared",
            field=models.CharField(
                default="p",
                max_length=1,
                choices=[("p", "private"), ("c", "company"), ("w", "world")],
            ),
            preserve_default=False,
        ),
    ]
