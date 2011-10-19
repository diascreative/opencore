# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz.org
#               2010-2011 Large Blue
#               Fergus Doyle: fergus.doyle@largeblue.com
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.  You may not use, modify or distribute
# this program under any other version of the GNU General Public License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""
A stupid HTML to Ascii converter

$Id: sgml.py 1493 2006-04-07 06:47:10Z ajung $
"""

import re
import sys
import StringIO

from opencore.utilities.converters.baseconverter import BaseConverter
from opencore.utilities.converters.StripTagParser import StripTagParser
from opencore.utilities.converters.entities import convert_entities

default_encoding = sys.getdefaultencoding()
encoding_reg = re.compile('encoding="(.*?)"')

class Converter(BaseConverter):

    content_type = ('text/sgml', 'text/xml')
    content_description = "Converter SGML to ASCII"

    def convert(self, filename, encoding, mimetype):

        # XXX: dont read entire file into memory
        doc = open(filename, 'r').read()

        # Use encoding from XML preamble if present
        mo = encoding_reg.search(doc)
        if mo:
            encoding = mo.group(1)

        if not encoding:
            encoding = default_encoding
        
        if not isinstance(doc, unicode):
            doc = unicode(doc, encoding, 'replace')
        doc = convert_entities(doc)
        doc = doc.encode('utf-8')
        p = StripTagParser()
        p.feed(doc)
        p.close()
        return StringIO.StringIO(p), 'utf-8'

SGMLConverter = Converter()
