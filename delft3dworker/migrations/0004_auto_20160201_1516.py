# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-02-01 15:16
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0003_auto_20160128_0349"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ModelRun",
            new_name="Delft3DWorker",
        ),
    ]
