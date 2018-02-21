# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0044_auto_20160713_1222'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scenario',
            name='state',
            field=models.CharField(default=b'CREATED', max_length=64),
        ),
        migrations.AlterField(
            model_name='scene',
            name='state',
            field=models.CharField(default=b'CREATED', max_length=256),
        ),
    ]
