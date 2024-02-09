# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0011_auto_20160317_1116"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scene",
            name="info",
            field=jsonfield.fields.JSONField(default=dict, blank=True),
        ),
    ]
