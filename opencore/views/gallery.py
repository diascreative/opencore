"""
Views handling gallery widget requests
"""
import logging
import urllib

from colander import SchemaNode, MappingSchema, Function
from deform import FileData, Form, ValidationFailure
from deform.widget import FileUploadWidget
from repoze.bfg.exceptions import NotFound
from webob import Response

from opencore.views.forms import is_image, tmpstore

log = logging.getLogger(__name__)

class ImageUploadSchema(MappingSchema):
    image = SchemaNode(
            FileData(),
            widget=FileUploadWidget(tmpstore),
            description=(
                "Choose an image file to upload"
                ),
            validator=Function(is_image),
            )

def image_upload(context, request):
    data = {'api': request.api, 'form': None, 'thumb_url': None}
    form = Form(ImageUploadSchema(), buttons=('Submit',))
    if request.method == "POST":
        controls = request.POST.items()
        log.debug('form controls: %r',controls)
        try:
            validated = form.validate(controls)
        except ValidationFailure, e:
            data['form'] = e.render()
        else:
            # Handle success
            log.debug('validated data: %s', validated)
            uid = validated['image']['uid']
            data['thumb_url'] = '/'.join([ request.api.app_url,
                                           'gallery_image_thumb_layout', 
                                           uid ])
    else:
        data['form'] = form.render({})

    return data

def _find_tmp_thumb(request):
    try:
        uid = request.subpath[0]
        image_file = tmpstore[uid]
        return image_file
    except (IndexError, KeyError), e:
        log.warning("Gallery thumbnail not found: %s", e)
        raise NotFound()

def image_thumb_layout(context, request):
    """
    This view renders HTML containing an image preview
    """
    thumb = _find_tmp_thumb(request)
    data = {'thumb_url':  thumb['preview_url'], 'uid': thumb['uid']}
    return data

def image_thumb(context, request):
    thumb = _find_tmp_thumb(request)
    data = thumb['fp'].read()
    thumb['fp'].seek(0)
    mimetype = thumb['mimetype']
    return Response(data, content_type=mimetype)
