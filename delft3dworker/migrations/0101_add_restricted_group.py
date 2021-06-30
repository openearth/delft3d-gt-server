from django.db import migrations

restricted_world_permissions = [
    "view_scenario",
    "view_scene",
    "view_template",
]


def forwards_func(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    db_alias = schema_editor.connection.alias

    restricted_world, _ = Group.objects.using(db_alias).get_or_create(
        name="access:world_restricted"
    )
    for permission_code in restricted_world_permissions:
        perm = Permission.objects.using(db_alias).get(codename=permission_code)
        restricted_world.permissions.add(perm)


def reverse_func(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    db_alias = schema_editor.connection.alias
    Group.objects.using(db_alias).filter(name="access:world_restricted").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0100_alter_scene_options"),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
