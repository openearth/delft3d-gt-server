# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0078_auto_20161116_0958'),
    ]

    operations = [
        migrations.AddField(
            model_name='container',
            name='delft3d_version',
            field=models.CharField(default=b'Deltares, FLOW2D3D Version 6.02.07.6118', max_length=128),
        ),
        migrations.AddField(
            model_name='container',
            name='svn_repos_url',
            field=models.URLField(default=b'http://delft3dgt.openearth.eu/repos/tags/v0.7.2'),
        ),
        migrations.AddField(
            model_name='container',
            name='svn_revision',
            field=models.CharField(default=b'356', max_length=16),
        ),
    ]
