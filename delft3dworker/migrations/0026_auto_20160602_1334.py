# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0025_auto_20160602_0955"),
    ]

    operations = [
        migrations.RenameField(
            model_name="scenario",
            old_name="template_url",
            new_name="template",
        ),
        migrations.RenameField(
            model_name="scene",
            old_name="scenario_url",
            new_name="scenario",
        ),
    ]
