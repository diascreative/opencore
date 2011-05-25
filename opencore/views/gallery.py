"""
Views handling gallery widget requests
"""
import logging
import urllib

from colander import SchemaNode, MappingSchema, Function
from deform import FileData, Form, ValidationFailure
from deform.widget import FileUploadWidget
from repoze.bfg.exceptions import NotFound

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
    data = {'form': None, 'preview_url': None}
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
            mimetype = validated['image']['mimetype']
            preview_url = tmpstore.preview_url(uid)
            preview_params = urllib.urlencode({'mimetype': mimetype})
            data['preview_url'] = '?'.join([preview_url, preview_params])
    else:
        data['form'] = form.render({})

    return data

def image_preview_layout(context, request):
    """
    This view renders HTML containing an image preview
    """
    data = {}
    try:
        uid = request.subpath[0]
        data['image_url'] = '?'.join([
            tmpstore.preview_url(uid),
            urllib.urlencode(request.GET)
            ])
    except IndexError, KeyError:
        raise NotFound()
    return data

def image_preview(context, request):
    try:
        uid = request.subpath[0]
        image_file = tmpstore[uid]
        mimetype = request.params['mimetype']
    except (IndexError, KeyError), e:
        log.warning(e.message)
        raise NotFound()
    print "***", image_file

