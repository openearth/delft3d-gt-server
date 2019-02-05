# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0035_auto_20160527_1326'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scene',
            name='parameters_hash',
            field=models.CharField(max_length=64, blank=True),
        ),
    ]
