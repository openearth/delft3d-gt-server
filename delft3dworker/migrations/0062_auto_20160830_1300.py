# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0061_auto_20160830_1300'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='task_starttime',
            field=models.DateTimeField(default=datetime.datetime(2016, 8, 30, 13, 0, 42, 990726, tzinfo=utc), blank=True),
        ),
    ]
