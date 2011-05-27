from cgi import escape
from pprint import pformat
import operator
import string
import random

from colander import (
        null,
        Invalid,
        )
from deform import (
    Form,
    ValidationFailure,
    )
from deform.widget import (
    CheckboxWidget,
    FileUploadWidget,
    Widget,
    FormWidget,
    )
from persistent.mapping import PersistentMapping
from PIL import Image

from opencore.events import (
    ObjectWillBeModifiedEvent,
    ObjectModifiedEvent,
    )
from opencore.models.files import CommunityFolder
from opencore.models.interfaces import (
    ICommunityFile,
    )
from opencore.utilities.image import thumb_url
from opencore.utilities import oembed
from pkg_resources import resource_filename
from repoze.bfg.security import (
    has_permission,
    authenticated_userid,
    )
from repoze.bfg.threadlocal import get_current_request
from repoze.bfg.url import model_url
from repoze.lemonade.content import create_content
from urllib import quote
from webob.exc import HTTPFound
from zope.component.event import objectEventNotify

import logging
import re

log = logging.getLogger(__name__)

### Set form template paths

default_template_path = (
        resource_filename('opencore','views/templates/widgets'),
        resource_filename('deform', 'templates')
        )
app_template_path = list(Form.default_renderer.loader.search_path)

# Append opencore and deform template paths to list of app-specific paths
for path in default_template_path:
    if path not in app_template_path:
        app_template_path.append(path)

Form.set_zpt_renderer(app_template_path)

### Helpers

class instantiate:
    """
    A class decorator to make make writing
    schemas in Controller classes easier
    """
    def __init__(self,*args,**kw):
        self.args,self.kw = args,kw
    def __call__(self,class_):
        return class_(*self.args,**self.kw)
    
def _get_manage_actions(community, request):
    # XXX - this isn't very pluggable :-(
    
    # Filter the actions based on permission in the **community**
    actions = []
    if has_permission('moderate', community, request):
        actions.append(('Manage Members', 'manage.html'))
        actions.append(('Add', 'invite_new.html'))

    return actions

# Temporary stores

class DummyTempStore:

    def get(self,name,default=None):
        return default

    def __getitem__(self,name):
        raise KeyError(name)

    def __setitem__(self,name,value):
        pass

    def __contains__(self,name):
        return False

    def preview_url(self,name):
        return None

class MemoryTempStore(dict):
    def preview_url(self, name):
        return '/gallery_image_thumb/' + name

class VideoTempStore(MemoryTempStore):
    def preview_url(self, name):
        return '/video_thumb/' + name

tmpstore = MemoryTempStore()
video_tmpstore = VideoTempStore()

### Controllers for form submission
    
class BaseController(object):

    buttons=('cancel','save')

    def __init__(self, context, request, form_template=None):
        self.context = context
        self.request = request
        self.form_template = form_template
        self.api = request.api
        self.data = dict(
            api=self.api,
            )
        self.data['actions']=()
        
    def __call__(self):
        pre_call_result = self.pre_call()
        if pre_call_result:
            return pre_call_result
        
        request = self.request

        form = Form(self.Schema(), buttons=self.buttons)
        if self.form_template:
            form.widget = FormWidget(template=self.form_template)

        if self.buttons[-1] in request.POST:
            controls = request.POST.items()
            log.debug('form controls: %r',controls)
            try:
                validated = form.validate(controls)
            except ValidationFailure, e:
                self.data['form']=e.render()
                return self.data
            
            return self.handle_submit(validated)
        
        elif 'cancel' in request.POST:
            
            return HTTPFound(location=self.api.here_url)

        self.data['form']=form.render(self.form_defaults())
        return self.data
    
    def pre_call(self):
        """ Called as the very first thing in the view's __call__ method.
        """

    def form_defaults(self):
        """
        Return an appstruct to populate the form.
        """
        return null
    
    def handle_submit(self, validated):
        """
        Do whatever is required with the validated data
        passed in
        """
        raise NotImplementedError()

class ContentController(BaseController):

    def handle_content(self, content, request, validated):
        """
        Do whatever is required with the validated data
        and the content object passed in
        """
        raise NotImplementedError()

    def handle_submit(self, validated):
        context = self.context
        request = self.request
        
        objectEventNotify(ObjectWillBeModifiedEvent(context))

        
        self.handle_content(context,request,validated)

        # store who modified
        context.modified_by = authenticated_userid(request)
       
        objectEventNotify(ObjectModifiedEvent(context))
        location = model_url(context, request)
        msg = '?status_message='+quote(
            context.__class__.__name__+' edited'
            )
        return HTTPFound(location=location+msg)


class GalleryControllerMixin(object):

    @staticmethod
    def record_gallery_changes(context, validated, userid):

        if not 'gallery' in context:
            context['gallery'] = CommunityFolder(title='Gallery for %s' %
                    context.title, creator=userid)

        # Handle gallery items
        for item in validated['gallery']:
            item.record_change(context, userid)

    
### Widgets

class KarlUserWidget(Widget):
    """
    A widget to work with the #membersearch-input magic.
    The field this is user on *must* be called 'users'.
    """

    template = 'karluserwidget'

    def serialize(self, field, cstruct, readonly=False):
        if field.name!='users':
            raise Exception(
                "This widget must be used on a field named 'users'"
                )
        # For now we don't bother with cstruct parsing.
        # If we need to use this widget for edits, then we will have to
        return field.renderer(self.template, field=field, cstruct=())

    def deserialize(self, field, pstruct):
        return pstruct
    
class TOUWidget(CheckboxWidget):

    template='terms_of_use'


class AvatarWidget(FileUploadWidget):

    template = 'avatar'
    
    def __init__(self,**kw):
        FileUploadWidget.__init__(self, None, **kw)
        self.tmpstore = DummyTempStore()

    def serialize(self, field, cstruct, readonly=False):
        # Bluegh, wish there was a better way to get
        # api and profile in here :-/
        request = get_current_request()
        return field.renderer(self.template,
                              field=field,
                              api=request.api,
                              profile=request.context)


class ImageUploadWidget(FileUploadWidget):

    template = 'image_upload'

    def __init__(self, **kw):
        FileUploadWidget.__init__(self, None, **kw)
        self.tmpstore = tmpstore
        self.thumb_size = kw.get('thumb_size')

    def serialize(self, field, cstruct, readonly=False):
        if cstruct in (null, None):
            cstruct = {}
        if cstruct:
            uid = cstruct['uid']
            if not uid in self.tmpstore:
                self.tmpstore[uid] = cstruct

        template = readonly and self.readonly_template or self.template
        thumbnail_url = None
        params = dict(
                field=field, cstruct=cstruct, thumb_url=thumbnail_url,
                api=self.request.api, context=None, request=self.request
                )
        if hasattr(self, 'context') and hasattr(self, 'request'):
            # We're in an edit form as opposed to an add form
            image = self.context.get(field.name)
            if image is not None:
                params['thumb_url'] = thumb_url(image, self.request, self.thumb_size or (290, 216))
            params['context'] = self.context
        return field.renderer(template, **params)


IMAGE_PREVIEW_TEMPLATE = "&lt;img src=&quot;%s&quot; /&gt;"


class GalleryWidget(Widget):
    """
    A widget to work with galleries containing images and videos.
    """

    template = 'gallery'

    def serialize(self, field, cstruct, readonly=False):
        log.debug("*** GalleryWidget field: %s, cstruct: %s", field, cstruct)
        request = self.request
        api = request.api
        items = []
        if cstruct is null:
            pass
        elif isinstance(cstruct, CommunityFolder):
            for key, val in cstruct.items():
                item = {'key': key, 'order': val.order}
                if hasattr(val, 'is_image') and val.is_image:
                    item['thumb_url'] = api.thumb_url(val)
                    item['preview_code'] = IMAGE_PREVIEW_TEMPLATE % api.thumb_url(val)
                    item['type'] = 'image'
                else:
                    item['thumb_url'] = val['thumbnail_url']
                    item['preview_code'] = escape(val['html'], quote=True)
                    item['type'] = 'video'
                items.append(item)
        else:
            for order, citem in enumerate(cstruct):
                key = citem.get('key')
                if key:
                    item = self.context['gallery'][key]
                    if hasattr(item, 'is_image') and item.is_image:
                        thumb_url = api.thumb_url(item)
                        preview_code = IMAGE_PREVIEW_TEMPLATE % thumb_url
                    else:
                        thumb_url = item['thumbnail_url']
                        preview_code = escape(item['html'], quote=True)
                    items.append({
                              'key': key, 
                              'order': order,
                              'thumb_url': thumb_url,
                              'preview_code': preview_code,
                              'type': citem['type']
                              })
                else:
                    uid = citem.get('uid')
                    if uid:
                        item = {'uid': uid, 'type': citem['type'], 'order':
                                order}
                        if citem['type'] == 'video':
                            item['thumb_url'] = video_tmpstore[uid]['thumbnail_url']
                            item['preview_code'] = escape(video_tmpstore[uid]['thumbnail_url'], True)
                        else:
                            item['thumb_url'] = '/'.join([ 
                                               request.api.app_url,
                                               'gallery_image_thumb', 
                                               uid ])
                            item['preview_code'] = IMAGE_PREVIEW_TEMPLATE % item['thumb_url']
                        items.append(item)
        items.sort(key=operator.itemgetter('order'))
        params = dict(field=field, cstruct=(),
                request=self.request, api=self.request.api, items=items)
        return field.renderer(self.template, **params)

    def deserialize(self, field, pstruct):
        return pstruct

## Types

YOUTUBE_URL_REGEXP = re.compile("http:\/\/(www\.)?youtube.com\/watch.+")

def is_youtube_url(value):
    return YOUTUBE_URL_REGEXP.search(value)

class VideoEmbedData(object):
    """
    A colander type representing Youtube or Vimeo data
    """
    def serialize(self, node, value):
        if value is null:
            return null
        return value

    def deserialize(self, node, value):
        log.debug("VideoEmbedData *** field: %s, cstruct: %s", node, value)

        if value is null:
            return null

        consumer = oembed.OEmbedConsumer()
        if is_youtube_url(value):
            consumer.addEndpoint(oembed.OEmbedEndpoint('http://www.youtube.com/oembed',
                    'http://*.youtube.com/watch*'))
            consumer.addEndpoint(oembed.OEmbedEndpoint('http://www.youtube.com/oembed',
                    'http://youtube.com/watch*'))
        else:
            consumer.addEndpoint(oembed.OEmbedEndpoint('http://vimeo.com/api/oembed.json',
                'http://vimeo.com/*'))
            consumer.addEndpoint(oembed.OEmbedEndpoint('http://vimeo.com/api/oembed.json',
                'http://vimeo.com/groups/*/videos/*'))
        try:
            # Max width larger than 480 to support TV-format videos as well has
            # wide-screen
            data = consumer.embed(value, width=640, maxwidth=640, maxheight=500).getData()

        except Exception, e:
            log.warning(e.message, exc_info=True)
            raise Invalid(node,
                'Please enter a valid Vimeo or Youtube URL')

        log.debug("Video data from provider:\n%s", pformat(data))
        data['original_url'] = value

        random_id = lambda: ''.join([
            random.choice(string.uppercase+string.digits) for i in range(10)])

        while 1:
            uid = random_id()
            if video_tmpstore.get(uid) is None:
                data['uid'] = uid
                data['preview_url'] = video_tmpstore.preview_url(uid)
                video_tmpstore[uid] = data
                break
        return data


class GalleryPostItem(object):
    """
    Base class for gallery post data entries. 
    """

    def __init__(self, node, order, post_data):
        self.order = order
        self.new = ('uid' in post_data)
        self.delete = ('delete' in post_data)
        if self.new:
            if not self.delete:
                # Deleted before it was even saved. No need to get the data.
                try:
                    self.data = self.tmpstore[post_data['uid']]
                except KeyError, e:
                    raise Invalid(node, 
                        "There has been a problem uploading your image."
                        " Please try again. Key error: %s" % e)
        else:
            self.key = post_data.get('key')
            if not self.key:
                raise Invalid(node, 
                     "An image field must have either an uid or key")

    @staticmethod
    def make_key(context):
        key = 1
        while str(key) in context['gallery']:
            key += 1
        return str(key)


class GalleryImageItem(GalleryPostItem):

    def __init__(self, node, order, post_data):
        self.tmpstore = tmpstore
        super(GalleryImageItem, self).__init__(node, order, post_data)

    def create_image(self, context, userid):
        image = self.data
        content = create_content(
            ICommunityFile,
            title='Image of %s' % context.title,
            stream=image['fp'],
            mimetype=image['mimetype'],
            filename=image['filename'],
            creator=userid,
            )
        content.order = self.order
        key = self.make_key(context)
        context['gallery'][key] = content

    def record_change(self, context, userid):
        if self.new:
            self.create_image(context, userid)
        else:
            if self.delete:
                del context['gallery'][self.key]
            else:
                context['gallery'][self.key].order = self.order

class GalleryVideoItem(GalleryPostItem):

    def __init__(self, node, order, post_data):
        self.tmpstore = video_tmpstore
        super(GalleryVideoItem, self).__init__(node, order, post_data)

    def record_change(self, context, _userid):
        if self.new:
            key = self.make_key(context)
            data = self.data
            context['gallery'][key] = PersistentMapping(data)
            context['gallery'][key].order = self.order
        else:
            key = self.key
            if self.delete:
                del context['gallery'][key]
            else:
                context['gallery'][key].order = self.order


class GalleryList(object):
    """ 
    A colander type representing a list of gallery items.
    """

    def serialize(self, node, value):
        log.debug("GalleryList *** field: %s, cstruct: %s", node, value)
        if value is null:
            return null
        return value

    def deserialize(self, node, value):
        if value is null:
            return null
        result = []
        for order, post_data_entry in enumerate(value):
            item_type = post_data_entry.get('type')
            if item_type == 'image':
                item = GalleryImageItem(node, order, post_data_entry)
            elif item_type == 'video':
                item = GalleryVideoItem(node, order, post_data_entry)
            else:
                raise Invalid(node, 
                        "%s is not a valid gallery item type." % item_type)
            if not (item.new and item.delete):
                result.append(item)

        return result


### Validators

def is_image(value):
    msg = 'This file is not an image'
    if not value['mimetype'].startswith('image'):
        return msg
    fp = value['fp']
    try:
        Image.open(fp)
    except IOError:
        return msg
    fp.seek(0)
    return True

# Borrowed from:
# https://bitbucket.org/ianb/formencode/src/703c27be52b8/formencode/validators.py
# ...with modifications to make the scheme optional
url_re = re.compile(r'''
        ^((http|https)://
        (?:[%:\w]*@)?)?                           # authenticator
        (?P<domain>[a-z0-9][a-z0-9\-]{,62}\.)*  # (sub)domain - alpha followed by 62max chars (63 total)
        (?P<tld>[a-z]{2,})                      # TLD
        (?::[0-9]+)?                            # port

        # files/delims/etc
        (?P<path>/[a-z0-9\-\._~:/\?#\[\]@!%\$&\'\(\)\*\+,;=]*)?
        $
    ''', re.I | re.VERBOSE)

def valid_url(value):
    match = url_re.search(value)
    if match is not None and match.group('domain'):
       return  True
    return 'This is not a valid url'
