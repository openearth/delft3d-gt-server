# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-05-30 15:05
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0090_auto_20180530_0832'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scene',
            name='version',
        ),
        migrations.DeleteModel(
            name='Version_SVN',
        ),
    ]
