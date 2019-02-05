# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0085_merge'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='version_svn',
            options={'ordering': ['-revision'], 'verbose_name': 'SVN version', 'verbose_name_plural': 'SVN versions'},
        ),
    ]
