# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-05-30 15:06
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0091_auto_20180530_1505"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="container",
            name="scene",
        ),
        migrations.DeleteModel(
            name="Container",
        ),
    ]
