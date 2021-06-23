# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-02 13:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0005_delft3dworker_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="delft3dworker",
            name="workingdir",
            field=models.CharField(default="", editable=False, max_length=256),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="delft3dworker",
            name="uuid",
            field=models.CharField(editable=False, max_length=256),
        ),
    ]
