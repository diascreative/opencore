"""
a stupid HTML to Ascii converter

"""

import re
import StringIO
from opencore.utilities.converters.baseconverter import BaseConverter
from opencore.utilities.converters.entities import convert_entities
from opencore.utilities.converters.stripogram import html2text

charset_reg = re.compile('text/html.*?charset=(.*?)"', re.I|re.M)

class Converter(BaseConverter):

    content_type = ('text/html',)
    content_description = "Converter HTML to ASCII"

    def convert(self, filename, encoding=None, mimetype=None):
        # XXX: dont read entire file into memory
        doc = open(filename, 'r').read()

        # convert to unicode
        if not encoding:
            mo = charset_reg.search(doc)
            encoding = mo.group(1)
        doc = unicode(doc, encoding, 'replace')
        doc = convert_entities(doc)
        result = html2text(doc)

        # convert back to utf-8
        return StringIO.StringIO(result.encode('utf-8')), 'utf-8'

HTMLConverter = Converter()
