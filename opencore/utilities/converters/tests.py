# -*- coding: iso-8859-15 -*-

import unittest

class BaseConverterTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.utilities.converters.baseconverter import BaseConverter
        return BaseConverter

    def _makeOne(self,
                 content_type='text/plain',
                 content_description='Testing',
                 depends_on='ls',
                ):
        class Derived(self._getTargetClass()):
            def __init__(self):
                pass # suppress st00pid error checking
        derived = Derived()
        derived.content_type = (content_type,)
        derived.content_description = content_description
        derived.depends_on = depends_on
        return derived

    def test_getDescription(self):
        converter = self._makeOne()
        self.assertEqual(converter.getDescription(), 'Testing')

    def test_getType(self):
        converter = self._makeOne()
        self.assertEqual(converter.getType(), ('text/plain',))

    def test_getDependency(self):
        converter = self._makeOne()
        self.assertEqual(converter.getDependency(), 'ls')

    def test_isAvailable_empty_depends_on(self):
        converter = self._makeOne(depends_on='')
        self.assertEqual(converter.isAvailable(), 'always')

    def test_isAvailable_missing_depends_on(self):
        converter = self._makeOne(depends_on='nonesuchanimalcanexist')
        self.assertEqual(converter.isAvailable(), 'no')

    def test_isAvailable_valid_depends_on(self):
        converter = self._makeOne(depends_on='ls')
        self.assertEqual(converter.isAvailable(), 'yes')

    def test_hanging_converter(self):
        from opencore.utilities.converters.baseconverter import BaseConverter
        class HangingConverter(BaseConverter):
            content_type = "Up Your Nose"
            content_description = "With a Rubber Hose"
            timeout = 0.5
            def convert(self):
                return self.execute('grep . /dev/zero')

        out = HangingConverter().convert()
        self.assertEqual(0, len(out.read()))

class ConverterTests(unittest.TestCase):

    def testHTML(self):
        body = u'<html><body> alle Vögel Über Flügel und Tümpel</body></html>'
        utf8doc = u'alle Vögel Über Flügel und Tümpel'.encode('utf-8')

        import tempfile
        doc = tempfile.NamedTemporaryFile()
        doc.write(body.encode('iso-8859-15'))
        doc.flush()
        from opencore.utilities.converters import html
        C = html.Converter()
        stream, enc = C.convert(doc.name, 'iso-8859-15', 'text/html')
        text = stream.read().strip()
        self.assertEqual(enc, 'utf-8')
        self.assertEqual(text, utf8doc)

        import tempfile
        doc = tempfile.NamedTemporaryFile()
        doc.write(body.encode('utf-8'))
        doc.flush()
        stream, enc = C.convert(doc.name, 'utf8', 'text/html')
        text = stream.read().strip()
        self.assertEqual(enc, 'utf-8')
        self.assertEqual(text, utf8doc)

    def testHTMLWithEntities(self):
        body = (u'<html><body> alle V&ouml;gel &Uuml;ber Fl&uuml;gel '
                u'und T&uuml;mpel</body></html>')
        utf8doc = u'alle Vögel Über Flügel und Tümpel'.encode('utf-8')
        from opencore.utilities.converters import html

        import tempfile
        C = html.Converter()

        doc = tempfile.NamedTemporaryFile()
        doc.write(body.encode('iso-8859-15'))
        doc.flush()
        stream, enc = C.convert(doc.name, 'iso-8859-15', 'text/html')
        text = stream.read().strip()
        self.assertEqual(enc, 'utf-8')
        self.assertEqual(text, utf8doc)

        doc = tempfile.NamedTemporaryFile()
        doc.write(body.encode('utf-8'))
        doc.flush()
        stream, enc = C.convert(doc.name, 'utf8', 'text/html')
        text = stream.read().strip()
        self.assertEqual(enc, 'utf-8')
        self.assertEqual(text, utf8doc)

    def testHTMLWithNumericEntities(self):
        body = (u'<html><body>Non&#160;breaking&#160;space.</body></html>')
        utf8doc = u'Non breaking space.'.encode('utf-8')
        from opencore.utilities.converters import html

        import tempfile
        C = html.Converter()

        doc = tempfile.NamedTemporaryFile()
        doc.write(body.encode('iso-8859-15'))
        doc.flush()
        stream, enc = C.convert(doc.name, 'iso-8859-15', 'text/html')
        text = stream.read().strip()
        self.assertEqual(enc, 'utf-8')
        self.assertEqual(text, utf8doc)

        doc = tempfile.NamedTemporaryFile()
        doc.write(body.encode('utf-8'))
        doc.flush()
        stream, enc = C.convert(doc.name, 'utf8', 'text/html')
        text = stream.read().strip()
        self.assertEqual(enc, 'utf-8')
        self.assertEqual(text, utf8doc)

    def testXML(self):
        body = ('<?xml version="1.0" encoding="iso-8859-15" ?><body> '
                'alle Vögel Über Flügel und Tümpel</body>')
        utf8doc = u'alle Vögel Über Flügel und Tümpel'.encode('utf-8')
        from opencore.utilities.converters import sgml
        import tempfile

        C = sgml.Converter()

        doc = tempfile.NamedTemporaryFile()
        doc.write(body)
        doc.flush()
        # encoding should be taken from the preamble
        stream, enc = C.convert(doc.name, 'utf8', 'text/html')
        text = stream.read().strip()
        self.assertEqual(enc, 'utf-8')
        self.assertEqual(text, utf8doc)

    def testOpenOffice(self):
        import os
        fn = os.path.join(os.path.dirname(__file__), 'fixtures',
                          'test.sxw')
        from opencore.utilities.converters import ooffice

        C = ooffice.Converter()
        # encoding should be taken from the preamble
        stream, enc = C.convert(fn, 'utf8', 'text/html')
        expected = (u'Viel Vögel sprangen artig in den Tüpel und über '
                    u'Feld und Wüste')
        expected_words = [w.strip() for w in expected.encode(enc).split()
                          if w.strip()]
        got_words = [w.strip() for w in stream.read().split() if w.strip()]
        self.assertEqual(got_words, expected_words)

    def testPDF(self):
        import os
        fn = os.path.join(os.path.dirname(__file__), 'fixtures',
                          'test.pdf')
        from opencore.utilities.converters import pdf

        C = pdf.Converter()
        if C.isAvailable() == 'yes':
            # encoding should be taken from the preamble
            stream, enc = C.convert(fn, 'utf8', 'text/html')
            expected = (u'Viel Vögel sprangen artig in den Tüpel und über '
                        u'Feld und Wüste')
            expected_words = [w.strip() for w in expected.encode(enc).split() if
                              w.strip()]
            got_words = [w.strip() for w in stream.read().split() if w.strip()]
            self.assertEqual(got_words, expected_words)
        else:
            import logging
            logging.debug('Omitting test for PDF converter as the converter is unavailable')


