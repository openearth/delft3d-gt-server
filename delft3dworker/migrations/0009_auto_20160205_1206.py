# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-05 12:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0008_delft3dworker_info"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="delft3dworker",
            name="progress",
        ),
        migrations.RemoveField(
            model_name="delft3dworker",
            name="timeleft",
        ),
        migrations.AddField(
            model_name="delft3dworker",
            name="fileurl",
            field=models.CharField(default="", editable=False, max_length=256),
            preserve_default=False,
        ),
    ]
