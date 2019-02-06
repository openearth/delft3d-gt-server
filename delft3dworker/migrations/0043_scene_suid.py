# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0042_remove_scene_suid'),
    ]

    operations = [
        migrations.AddField(
            model_name='scene',
            name='suid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
