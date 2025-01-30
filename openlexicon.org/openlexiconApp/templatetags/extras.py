from django import template
from openlexiconApp.utils import DbColMap

register = template.Library()

@register.filter
def stringify_dict(col_dict):
    return DbColMap.stringify_dict(col_dict)
