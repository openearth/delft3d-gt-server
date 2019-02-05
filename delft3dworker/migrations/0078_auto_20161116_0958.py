# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0077_auto_20161018_0925'),
    ]

    operations = [
        migrations.AddField(
            model_name='scene',
            name='date_created',
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
        migrations.AddField(
            model_name='scene',
            name='date_started',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
