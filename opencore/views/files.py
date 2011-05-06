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

from webob import Response
from opencore.models.interfaces import IImage

def download_file_view(context, request):
    # To view image-ish files in-line, use thumbnail_view.
    f = context.blobfile.open()
    headers = [
        ('Content-Type', context.mimetype),
        ('Content-Length', str(context.size)),
    ]

    if 'save' in request.params:
        fname = context.filename
        if isinstance(fname, unicode):
            fname = fname.encode('utf-8')
        fname = fname.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        headers.append(
            ('Content-Disposition', 'attachment; filename=%s' % fname)
        )

    response = Response(headerlist=headers, app_iter=f)
    return response

def thumbnail_view(context, request):
    assert IImage.providedBy(context), "Context must be an image."
    filename = request.subpath[0] # <width>x<length>.jpg
    size = map(int, filename[:-4].split('x'))
    thumb = context.thumbnail(tuple(size))

    # XXX Allow browser caching be setting Last-modified and Expires
    #     and respecting If-Modified-Since requests with 302 responses.
    data = thumb.blobfile.open().read()
    return Response(body=data, content_type=thumb.mimetype)
