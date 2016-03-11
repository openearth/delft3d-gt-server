# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0003_remove_scene_json'),
    ]

    operations = [
        migrations.AlterField(
            model_name='celerytask',
            name='state',
            field=models.CharField(max_length=256, blank=True),
        ),
        migrations.AlterField(
            model_name='celerytask',
            name='state_meta',
            field=jsonfield.fields.JSONField(default=dict, blank=True),
        ),
        migrations.AlterField(
            model_name='scene',
            name='info',
            field=models.CharField(max_length=256, blank=True),
        ),
        migrations.AlterField(
            model_name='scene',
            name='state',
            field=models.CharField(max_length=256, blank=True),
        ),
    ]
