# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0002_celerytask_state_meta'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scene',
            name='json',
        ),
    ]
