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
