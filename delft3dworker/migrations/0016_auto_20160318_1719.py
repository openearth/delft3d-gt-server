# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0015_template'),
    ]

    operations = [
        migrations.RenameField(
            model_name='template',
            old_name='name',
            new_name='templatename',
        ),
        migrations.RenameField(
            model_name='template',
            old_name='json',
            new_name='variables',
        ),
        migrations.AddField(
            model_name='template',
            name='description',
            field=models.CharField(max_length=256, blank=True),
        ),
        migrations.AddField(
            model_name='template',
            name='email',
            field=models.CharField(max_length=256, blank=True),
        ),
        migrations.AddField(
            model_name='template',
            name='label',
            field=models.CharField(max_length=256, blank=True),
        ),
        migrations.AddField(
            model_name='template',
            name='model',
            field=models.CharField(max_length=256, blank=True),
        ),
        migrations.AddField(
            model_name='template',
            name='site',
            field=models.CharField(max_length=256, blank=True),
        ),
        migrations.AddField(
            model_name='template',
            name='version',
            field=models.IntegerField(default=1, max_length=256, blank=True),
            preserve_default=False,
        ),
    ]
