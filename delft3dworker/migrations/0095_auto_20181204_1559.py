# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-04 15:59
from __future__ import unicode_literals

import delft3dworker.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0094_auto_20181204_1539'),
    ]

    operations = [
        migrations.AlterField(
            model_name='template',
            name='yaml_template',
            field=models.FileField(default='', upload_to=delft3dworker.models.parse_argo_workflow),
        ),
    ]
