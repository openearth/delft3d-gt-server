# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0029_auto_20160531_0908"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="scenario",
            options={"permissions": (("view_scenario", "View Scenario"),)},
        ),
        migrations.AlterModelOptions(
            name="scene",
            options={"permissions": (("view_scene", "View Scene"),)},
        ),
    ]
