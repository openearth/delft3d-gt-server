from django.db import migrations
from guardian.shortcuts import (
    assign_perm,
    get_groups_with_perms,
    get_users_with_perms,
    remove_perm,
)


def forwards_func(apps, schema_editor):
    Scene = apps.get_model("delft3dworker", "Scene")
    Group = apps.get_model("auth", "Group")
    db_alias = schema_editor.connection.alias

    restricted_world = Group.objects.using(db_alias).get(name="access:world_restricted")

    for scene in Scene.objects.using(db_alias).all():

        # if a user has view permission on a scene,
        # the user also has a extended_view
        for user, _ in get_users_with_perms(
            scene,
            attach_perms=True,
            with_group_users=False,
            only_with_perms_in=("view_scene",),
        ).items():
            assign_perm("extended_view_scene", user, scene)

        # if a group has a view permission on a scene,
        # the group also has a extended view
        for group, permissions in get_groups_with_perms(
            scene, attach_perms=True
        ).items():
            if "view_scene" in permissions:
                assign_perm("extended_view_scene", group, scene)

            # if the world group has a view permission
            # we also add view to the restricted world group
            if "view_scene" in permissions and group.name == "access:world":
                assign_perm("view_scene", restricted_world, scene)


def reverse_func(apps, schema_editor):
    Scene = apps.get_model("delft3dworker", "Scene")
    db_alias = schema_editor.connection.alias

    for scene in Scene.objects.using(db_alias).all():
        for user, _ in get_users_with_perms(
            scene,
            attach_perms=True,
            with_group_users=False,
            only_with_perms_in=("extended_view_scene",),
        ).items():
            remove_perm("extended_view_scene", user, scene)

        for group, permissions in get_groups_with_perms(
            scene, attach_perms=True
        ).items():
            if "extended_view_scene" in permissions:
                remove_perm("extended_view_scene", group, scene)

            if "view_scene" in permissions and group.name == "access:world_restricted":
                remove_perm("view_scene", group, scene)


class Migration(migrations.Migration):

    dependencies = [
        ("delft3dworker", "0100_alter_scene_options"),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
