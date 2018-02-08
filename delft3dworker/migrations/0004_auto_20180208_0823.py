# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-02-08 08:23
from __future__ import unicode_literals

import delft3dworker.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0003_auto_20180207_1309'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='container_starttime',
            field=models.DateTimeField(blank=True, default=delft3dworker.utils.tz_now),
        ),
        migrations.AlterField(
            model_name='container',
            name='container_stoptime',
            field=models.DateTimeField(blank=True, default=delft3dworker.utils.tz_now),
        ),
        migrations.AlterField(
            model_name='container',
            name='task_starttime',
            field=models.DateTimeField(blank=True, default=delft3dworker.utils.tz_now),
        ),
        migrations.AlterField(
            model_name='scene',
            name='date_created',
            field=models.DateTimeField(blank=True, default=delft3dworker.utils.tz_now),
        ),
    ]
