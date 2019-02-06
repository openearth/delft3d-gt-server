# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0024_auto_20160602_0715'),
    ]

    operations = [
        migrations.RenameField(
            model_name='scenario',
            old_name='template',
            new_name='template_url',
        ),
        migrations.RenameField(
            model_name='scene',
            old_name='scenario',
            new_name='scenario_url',
        ),
    ]
