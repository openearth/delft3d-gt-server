# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0027_merge'),
    ]

    operations = [
        migrations.RenameField(
            model_name='scenario',
            old_name='owner_url',
            new_name='owner',
        ),
        migrations.RenameField(
            model_name='scene',
            old_name='owner_url',
            new_name='owner',
        ),
    ]
