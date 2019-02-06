# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0022_auto_20160525_1906'),
    ]

    operations = [
        migrations.RenameField(
            model_name='template',
            old_name='templatename',
            new_name='name',
        ),
        migrations.RenameField(
            model_name='template',
            old_name='variables',
            new_name='sections',
        ),
        migrations.RemoveField(
            model_name='template',
            name='description',
        ),
        migrations.RemoveField(
            model_name='template',
            name='email',
        ),
        migrations.RemoveField(
            model_name='template',
            name='groups',
        ),
        migrations.RemoveField(
            model_name='template',
            name='label',
        ),
        migrations.RemoveField(
            model_name='template',
            name='model',
        ),
        migrations.RemoveField(
            model_name='template',
            name='site',
        ),
        migrations.RemoveField(
            model_name='template',
            name='version',
        ),
        migrations.AddField(
            model_name='template',
            name='meta',
            field=jsonfield.fields.JSONField(default=dict, blank=True),
        ),
    ]
