# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0020_auto_20160422_2304"),
    ]

    operations = [
        migrations.RenameField(
            model_name="scenario",
            old_name="parameters",
            new_name="input_parameters",
        ),
        migrations.AddField(
            model_name="scenario",
            name="scenes_parameters",
            field=jsonfield.fields.JSONField(default=dict, blank=True),
        ),
    ]
