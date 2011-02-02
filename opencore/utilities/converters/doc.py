"""
WinWord converter

"""

import os
import sys

from opencore.utilities.converters.baseconverter import BaseConverter
here = os.path.dirname(__file__)
wvConf_file = os.path.join(here, 'wvText.xml')

class Converter(BaseConverter):

    content_type = ('application/msword',
                    'application/ms-word','application/vnd.ms-word')
    content_description = "Microsoft Word"
    depends_on = 'wvWare'

    def convert(self, filename, encoding, mimetype):
        """Convert WinWord document to raw text"""
        
        if sys.platform == 'win32':
            return self.execute(
                'wvWare -c utf-8 --nographics -x "%s" "%s"' % (
                wvConf_file, filename)), 'utf-8'
        else:
            return self.execute(
                'wvWare -c utf-8 --nographics -x "%s" "%s"' % (
                wvConf_file, filename)), 'utf-8'

DocConverter = Converter()
