# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0056_auto_20160825_0548'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='container_type',
            field=models.CharField(default=b'preprocess', max_length=16, choices=[(b'preprocess', b'preprocess'), (b'delft3d', b'delft3d'), (b'process', b'process'), (b'postprocess', b'postprocess'), (b'export', b'export')]),
        ),
    ]
