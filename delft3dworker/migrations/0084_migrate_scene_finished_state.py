# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0083_auto_20170412_0907'),
    ]

    operations = [
        migrations.RunSQL(
            [("UPDATE delft3dworker_scene SET phase = 500 WHERE phase = 50;")],
            [("UPDATE delft3dworker_scene SET phase = 50 WHERE phase = 500;")],
        )
    ]
