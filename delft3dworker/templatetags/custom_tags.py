from django import template

register = template.Library()


def divtime(value, arg):
    """Removes all values of arg from the given string"""
    if value is None or arg is None:
        return 0
    else:
        return value.total_seconds() / arg.total_seconds() * 100. if arg != 0 else 0


register.filter('divtime', divtime)
