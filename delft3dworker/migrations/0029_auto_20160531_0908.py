# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0028_auto_20160602_1433"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="scenario",
            options={
                "default_permissions": ("view",),
                "permissions": (("view_scenario", "View Scenario"),),
            },
        ),
        migrations.AlterModelOptions(
            name="scene",
            options={
                "default_permissions": ("view",),
                "permissions": (("view_scene", "View Scene"),),
            },
        ),
        migrations.AlterModelOptions(
            name="template",
            options={
                "default_permissions": ("view",),
                "permissions": (("view_template", "View Template"),),
            },
        ),
    ]
