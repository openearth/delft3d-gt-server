# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0018_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='scenario',
            name='parameters',
            field=jsonfield.fields.JSONField(default=dict, blank=True),
        ),
        migrations.AddField(
            model_name='scenario',
            name='template',
            field=models.OneToOneField(null=True, to='delft3dworker.Template', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='scene',
            name='parameters',
            field=jsonfield.fields.JSONField(default=dict, blank=True),
        ),
        migrations.AddField(
            model_name='scene',
            name='scenario',
            field=models.ForeignKey(to='delft3dworker.Scenario', null=True, on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='template',
            name='version',
            field=models.IntegerField(blank=True),
        ),
    ]
