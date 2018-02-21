# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0025_auto_20160602_0955'),
    ]

    operations = [
        migrations.RenameField(
            model_name='scenario',
            old_name='template_url',
            new_name='template',
        ),
        migrations.RenameField(
            model_name='scene',
            old_name='scenario_url',
            new_name='scenario',
        ),
    ]
