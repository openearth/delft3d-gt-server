# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0039_auto_20160706_1418"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchform",
            name="templates",
            field=jsonfield.fields.JSONField(default=[]),
        ),
    ]
