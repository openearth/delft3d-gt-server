# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0016_auto_20160318_1719"),
    ]

    operations = [
        migrations.AddField(
            model_name="template",
            name="groups",
            field=jsonfield.fields.JSONField(default=dict, blank=True),
        ),
    ]
