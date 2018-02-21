# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models
import delft3dworker.models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0083_auto_20170412_0907'),
    ]

    operations = [
        migrations.CreateModel(
            name='Version_SVN',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('release', models.CharField(max_length=256, db_index=True)),
                ('revision', models.PositiveSmallIntegerField(db_index=True)),
                ('versions', jsonfield.fields.JSONField(default={})),
                ('url', models.URLField()),
                ('changelog', models.CharField(max_length=256)),
                ('reviewed', models.BooleanField(default=False)),
            ],
        ),
        migrations.RemoveField(
            model_name='container',
            name='version',
        ),
        migrations.AlterField(
            model_name='scene',
            name='workflow',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'main workflow'), (1, b'redo processing workflow'), (2, b'redo postprocessing workflow'), (3, b'redo processing and postprocessing workflow')]),
        ),
        migrations.AddField(
            model_name='scene',
            name='version',
            field=models.ForeignKey(default=delft3dworker.models.default_svn_version, to='delft3dworker.Version_SVN'),
        ),
    ]
