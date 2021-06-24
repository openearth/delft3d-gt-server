# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0051_auto_20160825_0935"),
    ]

    operations = [
        migrations.AddField(
            model_name="container",
            name="task_uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name="container",
            name="desired_state",
            field=models.CharField(
                default="non-existent",
                max_length=16,
                choices=[
                    ("non-existent", "non-existent"),
                    ("created", "created"),
                    ("restarting", "restarting"),
                    ("running", "running"),
                    ("paused", "paused"),
                    ("exited", "exited"),
                    ("dead", "dead"),
                    ("unknown", "unknown"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="container",
            name="docker_state",
            field=models.CharField(
                default="non-existent",
                max_length=16,
                choices=[
                    ("non-existent", "non-existent"),
                    ("created", "created"),
                    ("restarting", "restarting"),
                    ("running", "running"),
                    ("paused", "paused"),
                    ("exited", "exited"),
                    ("dead", "dead"),
                    ("unknown", "unknown"),
                ],
            ),
        ),
    ]
