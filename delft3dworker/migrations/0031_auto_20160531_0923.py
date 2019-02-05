# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0030_auto_20160531_0922'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='template',
            options={'permissions': (('view_template', 'View Template'),)},
        ),
    ]
