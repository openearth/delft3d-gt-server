# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0045_auto_20160714_0811"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scene",
            name="task_id",
            field=models.CharField(max_length=256, blank=True),
        ),
    ]
