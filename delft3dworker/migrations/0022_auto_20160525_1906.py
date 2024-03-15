# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0021_auto_20160525_1826"),
    ]

    operations = [
        migrations.RenameField(
            model_name="scenario",
            old_name="input_parameters",
            new_name="parameters",
        ),
    ]
