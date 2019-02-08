# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0055_container_docker_log'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='docker_id',
            field=models.CharField(default='', max_length=64, db_index=True, blank=True),
        ),
        migrations.AlterField(
            model_name='container',
            name='task_uuid',
            field=models.UUIDField(default=None, null=True, blank=True),
        ),
    ]
