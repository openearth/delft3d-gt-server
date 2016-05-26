# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0022_auto_20160525_1906'),
    ]

    operations = [
        migrations.AddField(
            model_name='scene',
            name='parameters_hash',
            field=models.CharField(unique=True, max_length=64, blank=True),
        ),
    ]
