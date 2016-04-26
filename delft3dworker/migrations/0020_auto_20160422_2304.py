# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delft3dworker', '0019_auto_20160421_1319'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='postprocessingtask',
            name='celerytask_ptr',
        ),
        migrations.RemoveField(
            model_name='postprocessingtask',
            name='scene',
        ),
        migrations.RemoveField(
            model_name='processingtask',
            name='celerytask_ptr',
        ),
        migrations.RemoveField(
            model_name='processingtask',
            name='scene',
        ),
        migrations.RemoveField(
            model_name='simulationtask',
            name='celerytask_ptr',
        ),
        migrations.RemoveField(
            model_name='simulationtask',
            name='scene',
        ),
        migrations.DeleteModel(
            name='CeleryTask',
        ),
        migrations.DeleteModel(
            name='PostprocessingTask',
        ),
        migrations.DeleteModel(
            name='ProcessingTask',
        ),
        migrations.DeleteModel(
            name='SimulationTask',
        ),
    ]
