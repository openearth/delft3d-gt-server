# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-05-29 18:34
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0088_auto_20180529_0942'),
    ]

    operations = [
        migrations.AddField(
            model_name='template',
            name='shortname',
            field=models.CharField(default='', max_length=256),
        ),
    ]
