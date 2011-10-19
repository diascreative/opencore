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

import re

from repoze.bfg.security import effective_principals
from repoze.bfg.url import model_url

from opencore.models.interfaces import ICommunityFile
from opencore.models.interfaces import IImage
from opencore.utils import find_tempfolder
from opencore.views.batch import get_catalog_batch
from opencore.views.utils import make_name

def thumb_url(image, request, size):
    """
    Return the url for displaying the image with dimensions bounded by given
    size.
    """
    assert IImage.providedBy(image), "Cannot take thumbnail of non-image."
    return model_url(image, request, 'thumb', '%dx%d.jpg' % size)

def get_images_batch(context,
                     request,
                     creator=None,   # 'My Recent' in imagedrawer
                     community=None, # 'This Community' in imagedrawer
                     batch_start=0,
                     batch_size=12,
                     sort_index='creation_date',
                     reverse=True,
                     batcher=get_catalog_batch):  # For unit testing
    search_params = dict(
        interfaces=[IImage,],
        allowed={'query': effective_principals(request), 'operator': 'or'},
        sort_index=sort_index,
        reverse=reverse,
        batch_start=batch_start,
        batch_size=batch_size,
    )

    if creator is not None:
        search_params['creator'] = creator
    if community is not None:
        search_params['path'] = community

    return batcher(context, request, **search_params)

TMP_IMG_RE = re.compile('(?P<pre><img[^>]+src=")'
                        '(?P<url>[^"]*/TEMP/(?P<tempid>[^/]+)'
                         '/thumb/(?P<width>\d+)x(?P<height>\d+)\.jpg)'
                        '(?P<post>"[^>]*>)')

def relocate_temp_images(doc, request):
    """
    Finds any <img> tags in the document body which point to images in the temp
    folder, moves those images to the attachments folder of the document and
    then rewrites the img tags to point to the new location.
    """
    attachments = doc.get_attachments()
    relocated_images = {}
    tempfolder = find_tempfolder(doc)

    def relocate(match):
        matchdict = match.groupdict()
        tempid = matchdict['tempid']
        if tempid in relocated_images:
            # Already relocated this one
            url = relocated_images[tempid]
        else:
            # Move temp image to attachments folder
            image = tempfolder[tempid]
            del tempfolder[tempid]
            name = make_name(attachments, image.filename)
            attachments[name] = image
            size = (int(matchdict['width']), int(matchdict['height']))
            url = thumb_url(image, request, size)
            relocated_images[tempid] = url
            workflow = get_workflow(ICommunityFile, 'security', image)
            if workflow is not None:
                workflow.initialize(image)

        return ''.join([matchdict['pre'], url, matchdict['post'],])

    doc.text = TMP_IMG_RE.sub(relocate, doc.text)
    tempfolder.cleanup()


extensions = {
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/png": "png",
}

# Convert types sent by IE to standard types
ie_types = {
    "image/x-png": "image/png",
    "image/pjpeg": "image/jpeg",
}

mimetypes = extensions.keys() + ie_types.keys()

def find_image(context, search='photo'):
    if search in context:
        return context[search]
    for ext in extensions.values():
        name = search + '.' + ext
        try:
            if name in context:
                return context[name]
        except (TypeError, KeyError): # if context is not iterable
            return None

#    if 'gallery' in context:
#        # try and find a suitable image in the gallery to use
#        for ob in context['gallery'].values():
#            # if ob is an external reference
#            if IExternalReference.providedBy(ob):
#                utility = getUtility(IExternalReferenceConverter, ob.content_provider)
#                return utility.get_thumbnail_url(ob.reference)
#            if ob.__name__.startswith('fullsized_'):
#                # skip fullsized images
#                continue
#            if ICommunityFile.providedBy(ob) and IGalleryRenderable.providedBy(ob):
#                return ob
    return None

