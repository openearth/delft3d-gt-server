# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0038_searchform"),
    ]

    operations = [
        migrations.AlterField(
            model_name="searchform",
            name="sections",
            field=jsonfield.fields.JSONField(default=[]),
        ),
    ]
