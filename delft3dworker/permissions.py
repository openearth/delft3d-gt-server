from rest_framework import permissions


class RedoScenePermission(permissions.BasePermission):
    """
    Custom Permission for Scene redo function. If a user has permission to view scene,
    they should have permission to redo scene. Apart from users' own scenes, allows all
    published runs to be redone by other users.
    """

    def has_object_permission(self, request, view, obj):
        can_view = request.user.has_perm('delft3dworker.view_scene', obj)
        return can_view


class ViewObjectPermissions(permissions.DjangoObjectPermissions):
    """
    Similar to `DjangoObjectPermissions`, but adding 'view' permissions.
    """
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }
