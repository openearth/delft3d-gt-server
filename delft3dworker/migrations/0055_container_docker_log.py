# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0054_auto_20160826_0747'),
    ]

    operations = [
        migrations.AddField(
            model_name='container',
            name='docker_log',
            field=models.TextField(default=b'', blank=True),
        ),
    ]
