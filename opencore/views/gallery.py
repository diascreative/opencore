"""
Views handling gallery widget requests
"""
import logging

from colander import SchemaNode, MappingSchema, Function
from deform import FileData, Form, ValidationFailure
from deform.widget import FileUploadWidget, TextInputWidget
from repoze.bfg.exceptions import NotFound
from webob import Response

from opencore.views.forms import (
        is_image,
        tmpstore,
        video_tmpstore,
        VideoEmbedData,
        )

log = logging.getLogger(__name__)


## Images


class ImageUploadSchema(MappingSchema):
    image = SchemaNode(
            FileData(),
            widget=FileUploadWidget(tmpstore),
            description="Choose an image file to upload",
            validator=Function(is_image),
            )


def image_upload(context, request):
    """
    The view that handles gallery images upload
    """
    data = {'api': request.api, 'form': None, 'thumb_url': None}
    form = Form(ImageUploadSchema(), buttons=('Submit',))
    if request.method == "POST":
        controls = request.POST.items()
        log.debug('form controls: %r', controls)
        try:
            validated = form.validate(controls)
        except ValidationFailure, e:
            data['form'] = e.render()
        else:
            # Handle success
            log.debug('validated data: %s', validated)
            uid = validated['image']['uid']
            data['thumb_url'] = '/'.join([request.api.app_url,
                                           'gallery_image_thumb_layout',
                                           uid])
    else:
        data['form'] = form.render({})

    return data


def _find_tmp_thumb(request, tmpstore=tmpstore):
    """
    Helper function to retrieve and image from the tempstore from a
    request that has the image uid in its URL path
    """
    try:
        uid = request.subpath[0]
        image_file = tmpstore[uid]
        return image_file
    except (IndexError, KeyError), e:
        log.warning("Gallery thumbnail not found: %s", e)
        raise NotFound()


def image_thumb_layout(context, request):
    """
    This view renders HTML containing an image preview. It is intended to be
    called via AJAX upon upload success.
    """
    thumb = _find_tmp_thumb(request)
    data = {'item_type': 'image', 'thumb_url':  thumb['preview_url'], 'uid': thumb['uid']}
    return data


def image_thumb(context, request):
    """
    This view serves an image from the tmpstore. It must have a uid as 
    its first subpath element.
    """
    thumb = _find_tmp_thumb(request)
    data = thumb['fp'].read()
    thumb['fp'].seek(0)
    mimetype = thumb['mimetype']
    return Response(data, content_type=mimetype)


## Videos


class VideoPostSchema(MappingSchema):
    video = SchemaNode(
            VideoEmbedData(),
            widget=TextInputWidget(),
            description="Please enter a youtube or vimeo URL",
            )


def video_post(context, request):
    """
    The view that handles gallery images upload
    """
    data = {'api': request.api, 'form': None, 'thumb_url': None}
    form = Form(VideoPostSchema(), buttons=('Submit',))
    if request.method == "POST":
        controls = request.POST.items()
        log.debug('form controls: %r', controls)
        try:
            validated = form.validate(controls)
        except ValidationFailure, e:
            data['form'] = e.render()
        else:
            # Handle success
            log.debug('validated data: %s', validated)
            uid = validated['video']['uid']
            data['thumb_url'] = '/'.join([request.api.app_url,
                                           'gallery_video_thumb_layout',
                                           uid])
    else:
        data['form'] = form.render({})

    return data


def video_thumb_layout(context, request):
    """
    This view renders HTML containing an image preview. It is intended to be
    called via AJAX upon upload success.
    """
    thumb = _find_tmp_thumb(request, tmpstore=video_tmpstore)
    data = {'item_type': 'video', 'thumb_url':  thumb['thumbnail_url'], 'uid': thumb['uid']}
    return data
