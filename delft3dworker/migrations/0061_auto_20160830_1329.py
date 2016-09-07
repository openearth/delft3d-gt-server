# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0060_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='container_starttime',
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
        migrations.AlterField(
            model_name='container',
            name='container_stoptime',
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
        migrations.AlterField(
            model_name='container',
            name='task_starttime',
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
    ]
