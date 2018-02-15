# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0079_auto_20161118_1341'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='container',
            name='delft3d_version',
        ),
        migrations.RemoveField(
            model_name='container',
            name='svn_repos_url',
        ),
        migrations.RemoveField(
            model_name='container',
            name='svn_revision',
        ),
        migrations.AddField(
            model_name='container',
            name='version',
            field=jsonfield.fields.JSONField(default=b'{}'),
        ),
    ]
