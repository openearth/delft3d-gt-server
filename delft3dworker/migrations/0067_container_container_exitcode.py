# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0066_auto_20160831_1311'),
    ]

    operations = [
        migrations.AddField(
            model_name='container',
            name='container_exitcode',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
