# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0009_auto_20160205_1206"),
    ]

    operations = [
        migrations.CreateModel(
            name="CeleryTask",
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
                ("uuid", models.CharField(max_length=256)),
                ("state", models.CharField(max_length=256, blank=True)),
                ("state_meta", jsonfield.fields.JSONField(default=dict, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="Scene",
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
                ("suid", models.CharField(max_length=256, editable=False)),
                ("workingdir", models.CharField(max_length=256)),
                ("fileurl", models.CharField(max_length=256)),
                ("name", models.CharField(max_length=256)),
                ("state", models.CharField(max_length=256, blank=True)),
                ("info", models.CharField(max_length=256, blank=True)),
                ("json", jsonfield.fields.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name="PostprocessingTask",
            fields=[
                (
                    "celerytask_ptr",
                    models.OneToOneField(
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="delft3dworker.CeleryTask",
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "scene",
                    models.ForeignKey(
                        to="delft3dworker.Scene", on_delete=models.CASCADE
                    ),
                ),
            ],
            bases=("delft3dworker.celerytask",),
        ),
        migrations.CreateModel(
            name="ProcessingTask",
            fields=[
                (
                    "celerytask_ptr",
                    models.OneToOneField(
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="delft3dworker.CeleryTask",
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "scene",
                    models.OneToOneField(
                        to="delft3dworker.Scene", on_delete=models.CASCADE
                    ),
                ),
            ],
            bases=("delft3dworker.celerytask",),
        ),
        migrations.CreateModel(
            name="SimulationTask",
            fields=[
                (
                    "celerytask_ptr",
                    models.OneToOneField(
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="delft3dworker.CeleryTask",
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "scene",
                    models.OneToOneField(
                        to="delft3dworker.Scene", on_delete=models.CASCADE
                    ),
                ),
            ],
            bases=("delft3dworker.celerytask",),
        ),
    ]
