# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0014_scenario"),
    ]

    operations = [
        migrations.CreateModel(
            name="Template",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=256)),
                ("json", jsonfield.fields.JSONField(default=dict, blank=True)),
            ],
        ),
    ]
