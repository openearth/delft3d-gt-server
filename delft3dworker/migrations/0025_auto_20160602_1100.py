# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("delft3dworker", "0024_auto_20160602_0715"),
    ]

    operations = [
        migrations.AddField(
            model_name="scenario",
            name="owner_url",
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
            ),
        ),
        migrations.AddField(
            model_name="scene",
            name="owner_url",
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
            ),
        ),
    ]
