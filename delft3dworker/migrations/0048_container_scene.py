# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0047_container"),
    ]

    operations = [
        migrations.AddField(
            model_name="container",
            name="scene",
            field=models.ForeignKey(
                default=None, to="delft3dworker.Scene", on_delete=models.CASCADE
            ),
            preserve_default=False,
        ),
    ]
