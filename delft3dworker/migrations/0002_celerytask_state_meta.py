# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='celerytask',
            name='state_meta',
            field=jsonfield.fields.JSONField(default=dict),
        ),
    ]
