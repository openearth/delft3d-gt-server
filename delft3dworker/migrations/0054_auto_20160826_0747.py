# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0053_auto_20160826_0747"),
    ]

    operations = [
        migrations.AlterField(
            model_name="container",
            name="task_uuid",
            field=models.UUIDField(default=uuid.uuid4, null=True, blank=True),
        ),
    ]
