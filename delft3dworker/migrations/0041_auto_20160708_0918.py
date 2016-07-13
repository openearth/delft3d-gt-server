# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0040_searchform_templates'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scene',
            name='scenario',
            field=models.ManyToManyField(to='delft3dworker.Scenario', blank=True),
        ),
    ]
