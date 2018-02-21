# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0058_container_task_starttime'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='task_starttime',
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
    ]
