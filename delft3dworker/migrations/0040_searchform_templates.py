# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0039_auto_20160706_1418'),
    ]

    operations = [
        migrations.AddField(
            model_name='searchform',
            name='templates',
            field=jsonfield.fields.JSONField(default=b'[]'),
        ),
    ]
