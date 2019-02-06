# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0052_auto_20160825_1404'),
    ]

    operations = [
        migrations.AlterField(
            model_name='container',
            name='task_uuid',
            field=models.UUIDField(default=uuid.uuid4, blank=True),
        ),
    ]
