from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.urls import reverse
from django.conf import settings

import os
import uuid
import re

from urllib.parse import urlencode

from functools import partial

from astropy.io import fits
from astropy.table import Table

register = template.Library()


@register.simple_tag
def make_uuid():
    return str(uuid.uuid1())


# Code borrowed from https://stackoverflow.com/a/3715794
@register.tag('make_list')
def make_list(parser, token):
    bits = token.contents.split()
    if len(bits) >= 4 and bits[-2] == "as":
        varname = bits[-1]
        items = bits[1:-2]
        return MakeListNode(items, varname)
    else:
        raise template.TemplateSyntaxError("%r expected format is 'item [item ...] as varname'" % bits[0])


class MakeListNode(template.Node):
    def __init__(self, items, varname):
        self.items = items
        self.varname = varname

    def render(self, context):
        items = map(template.Variable, self.items)
        context[self.varname] = [ i.resolve(context) for i in items ]
        return ""


@register.simple_tag
def free_disk_space():
    s = os.statvfs(settings.TASKS_PATH)
    return s.f_bavail*s.f_frsize


@register.simple_tag
def urlparams(*_, **kwargs):
    safe_args = {k: v for k, v in kwargs.items() if v is not None}
    if safe_args:
        return mark_safe('?{}'.format(urlencode(safe_args)))

    return ''
