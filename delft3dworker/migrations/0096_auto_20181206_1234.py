# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-06 12:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0095_auto_20181204_1559"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="version_docker",
            name="id",
        ),
        migrations.AlterField(
            model_name="version_docker",
            name="revision",
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
