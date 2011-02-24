_FLAVOR_FORMATS = {
    'longform': '%A, %B %d, %Y %I:%M %p',
    'shortform': '%d/%m/%Y'
    }

def convert(date, flavor):
    fmt = _FLAVOR_FORMATS[flavor]
    return date.strftime(fmt)

