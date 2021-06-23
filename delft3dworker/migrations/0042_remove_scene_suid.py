# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0041_auto_20160708_0918"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="scene",
            name="suid",
        ),
    ]
