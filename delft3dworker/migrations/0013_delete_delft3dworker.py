# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0012_auto_20160317_1423'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Delft3DWorker',
        ),
    ]
