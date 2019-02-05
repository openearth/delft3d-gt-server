# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0049_auto_20160825_0932'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='docker_id',
            field=models.CharField(default=b'', unique=True, max_length=64),
        ),
    ]
