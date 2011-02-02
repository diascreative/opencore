_FLAVOR_FORMATS = {
    'longform': '%A, %B %d, %Y %I:%M %p',
    }

def convert(date, flavor):
    fmt = _FLAVOR_FORMATS[flavor]
    return date.strftime(fmt)

