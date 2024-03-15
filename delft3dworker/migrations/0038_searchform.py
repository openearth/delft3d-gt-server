# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0037_auto_20160608_2304"),
    ]

    operations = [
        migrations.CreateModel(
            name="SearchForm",
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
                ("sections", jsonfield.fields.JSONField(default=dict, blank=True)),
            ],
        ),
    ]
