from django import template

register = template.Library()


def divtime(value, arg):
    """Custom tag to divide timedelta value by timedelta arg in html template"""
    if value is None or arg is None:
        return 0
    else:
        return value.total_seconds() / arg.total_seconds() * 100.0 if arg != 0 else 0


register.filter("divtime", divtime)
