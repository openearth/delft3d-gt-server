# Generated by Django 3.2.4 on 2021-06-21 16:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0098_auto_20200226_1452"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scene",
            name="phase",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "New"),
                    (6, "Idle: waiting for user input"),
                    (11, "Starting workflow"),
                    (12, "Running workflow"),
                    (13, "Removing workflow"),
                    (20, "Stopping workflow"),
                    (21, "Removing stopped workflow"),
                    (500, "Finished"),
                    (501, "Failed"),
                    (502, "Stopped"),
                ],
                default=0,
            ),
        ),
    ]
