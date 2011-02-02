import re
from opencore.utilities.converters.entities2uc import entitydefs

# Matches entities
entity_reg = re.compile('&(.*?);')

def handler(x):
    """ Callback to convert entity to UC """
    v = x.group(1)
    if v.startswith('#'):
        try:
            return unichr(int(v[1:]))
        except ValueError:
            pass
    return entitydefs.get(v, '')

def convert_entities(text):
    """ replace all entities inside a unicode string """
    assert isinstance(text, unicode)
    text = entity_reg.sub(handler, text)
    return text

