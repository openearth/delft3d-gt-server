# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0016_auto_20160318_1719'),
    ]

    operations = [
        migrations.AddField(
            model_name='template',
            name='groups',
            field=jsonfield.fields.JSONField(default=dict, blank=True),
        ),
    ]
