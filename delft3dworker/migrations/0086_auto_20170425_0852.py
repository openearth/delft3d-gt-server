# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0085_merge"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="version_svn",
            options={
                "ordering": ["-revision"],
                "verbose_name": "SVN version",
                "verbose_name_plural": "SVN versions",
            },
        ),
    ]
