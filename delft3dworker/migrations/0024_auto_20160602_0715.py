# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0023_auto_20160531_0851"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scenario",
            name="template",
            field=models.ForeignKey(
                to="delft3dworker.Template", null=True, on_delete=models.CASCADE
            ),
        ),
    ]
