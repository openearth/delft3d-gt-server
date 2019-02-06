# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0058_container_task_starttime'),
    ]

    operations = [
        migrations.AddField(
            model_name='container',
            name='container_starttime',
            field=models.DateTimeField(default=datetime.datetime(2016, 8, 30, 10, 42, 12, 820124, tzinfo=utc), blank=True),
        ),
        migrations.AddField(
            model_name='container',
            name='container_stoptime',
            field=models.DateTimeField(default=datetime.datetime(2016, 8, 30, 10, 42, 12, 820153, tzinfo=utc), blank=True),
        ),
        migrations.AlterField(
            model_name='container',
            name='task_starttime',
            field=models.DateTimeField(default=datetime.datetime(2016, 8, 30, 10, 42, 12, 820170, tzinfo=utc), blank=True),
        ),
    ]
