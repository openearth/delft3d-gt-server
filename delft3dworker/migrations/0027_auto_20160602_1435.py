# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0026_auto_20160602_1334'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scenario',
            name='template',
            field=models.ForeignKey(blank=True, to='delft3dworker.Template', null=True),
        ),
    ]
