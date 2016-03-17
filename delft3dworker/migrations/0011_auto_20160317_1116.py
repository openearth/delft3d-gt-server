# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-17 11:16
from __future__ import unicode_literals

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0010_celerytask_postprocessingtask_processingtask_scene_simulationtask'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scene',
            name='json',
        ),
        migrations.AlterField(
            model_name='scene',
            name='info',
            field=jsonfield.fields.JSONField(default=dict),
        ),
    ]
