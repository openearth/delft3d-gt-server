# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-28 09:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0002_modelruns"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ModelRuns",
            new_name="ModelRun",
        ),
        migrations.DeleteModel(
            name="WorkerTask",
        ),
    ]
