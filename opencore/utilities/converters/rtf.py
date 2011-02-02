# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz@sorosny.org
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
a simple RTF converter

$Id: rtf.py 1456 2006-02-08 14:10:27Z ajung $
"""

import os
import shutil
import tempfile
import xml.sax
from xml.sax.handler import ContentHandler

from opencore.utilities.converters.baseconverter import BaseConverter

class RTFtextHandler(ContentHandler):

    def characters(self, ch):
        self._data.write(ch.encode("UTF-8") + ' ')

    def startDocument(self):
        self._data = tempfile.NamedTemporaryFile()

    def getStream(self):
        self._data.seek(0)
        return self._data


class Converter(BaseConverter):

    content_type = ('application/rtf','text/rtf')
    content_description = "RTF"
    depends_on = 'rtf2xml'

    def convert(self, filename, encoding, mimetype):
        """ convert RTF Document """
        # XXX: dont read entire file into RAM
        handler = RTFtextHandler()
        xmlstr = self.execute('rtf2xml "%s"' % filename).read()
        xml.sax.parseString(xmlstr, handler)

        # rtf2xml quite rudely leaves behind temporary directories which it
        # appears to be using for unpacking embedded images.
        pict_dir = filename + "_rtf_pict_dir"
        if os.path.exists(pict_dir):
            shutil.rmtree(pict_dir)

        return handler.getStream(), 'utf-8'

RTFConverter = Converter()
