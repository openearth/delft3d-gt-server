# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations, models

import delft3dworker.models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0083_auto_20170412_0907"),
    ]

    operations = [
        migrations.CreateModel(
            name="Version_SVN",
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
                ("release", models.CharField(max_length=256, db_index=True)),
                ("revision", models.PositiveSmallIntegerField(db_index=True)),
                ("versions", jsonfield.fields.JSONField(default={})),
                ("url", models.URLField()),
                ("changelog", models.CharField(max_length=256)),
                ("reviewed", models.BooleanField(default=False)),
            ],
        ),
        migrations.RemoveField(
            model_name="container",
            name="version",
        ),
        migrations.AlterField(
            model_name="scene",
            name="workflow",
            field=models.PositiveSmallIntegerField(
                default=0,
                choices=[
                    (0, "main workflow"),
                    (1, "redo processing workflow"),
                    (2, "redo postprocessing workflow"),
                    (3, "redo processing and postprocessing workflow"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="scene",
            name="version",
            field=models.ForeignKey(
                default=delft3dworker.models.default_svn_version,
                to="delft3dworker.Version_SVN",
                on_delete=models.CASCADE,
            ),
        ),
    ]
