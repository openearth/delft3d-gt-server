from django.db import migrations

restricted_world_permissions = [
    "view_scenario",
    "view_scene",
    "view_template",
]


def forwards_func(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Scenario = apps.get_model("delft3dworker", "Scenario")
    Scene = apps.get_model("delft3dworker", "Scene")
    Template = apps.get_model("delft3dworker", "Template")

    db_alias = schema_editor.connection.alias

    restricted_world, _ = Group.objects.using(db_alias).get_or_create(
        name="access:world_restricted"
    )
    for model, permission_code in zip(
        [Scenario, Scene, Template], restricted_world_permissions
    ):
        content_type = ContentType.objects.get_for_model(model)
        print(model, content_type, permission_code)
        perm, _ = Permission.objects.using(db_alias).get_or_create(
            codename=permission_code, content_type=content_type
        )
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
