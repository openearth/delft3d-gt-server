# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0036_auto_20160527_1445'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scene',
            name='scenario',
            field=models.ManyToManyField(to='delft3dworker.Scenario'),
        ),
    ]
