from cStringIO import StringIO
import PIL.Image

from persistent import Persistent
from BTrees.OOBTree import OOBTree
from repoze.lemonade.content import create_content

from zope.interface import alsoProvides
from zope.interface import implements

from opencore.models.interfaces import IImage
from opencore.models.tool import ToolFactory
from opencore.models.interfaces import IToolFactory

from opencore.models.interfaces import ICommunityRootFolder
from opencore.models.interfaces import ICommunityFolder
from opencore.models.interfaces import ICommunityFile
from opencore.models.interfaces import IEventContainer

from repoze.folder import Folder
from ZODB.blob import Blob

class CommunityRootFolder(Folder):
    implements(ICommunityRootFolder, IEventContainer)
    title = u'Files'

class CommunityFolder(Folder):
    implements(ICommunityFolder, IEventContainer)
    modified_by = None

    def __init__(self, title, creator):
        super(CommunityFolder, self).__init__()
        self.title = unicode(title)
        self.creator = unicode(creator)
        self.modified_by = self.creator

class CommunityFile(Persistent):
    implements(ICommunityFile)
    modified_by = None  # Sorry, persistence
    is_image = False    # Sorry, persistence

    def __init__(self, title, stream, mimetype, filename, creator=u''):
        self.title = unicode(title)
        self.mimetype = mimetype
        self.filename = filename
        self.creator = unicode(creator)
        self.modified_by = self.creator
        self.blobfile = Blob()
        self.upload(stream)
        self._init_image()

    def _init_image(self):
        if not self.mimetype.startswith('image'):
            return

        try:
            image = PIL.Image.open(self.blobfile.open())
        except IOError:
            return

        self._thumbs = OOBTree()
        self.image_size = image.size
        self.is_image = True
        alsoProvides(self, IImage)

    def image(self):
        assert self.is_image, "Not an image."
        return PIL.Image.open(self.blobfile.open())

    def thumbnail(self, size):
        assert self.is_image, "Not an image."
        key = '%dx%d' % size
        thumbnail = self._thumbs.get(key, None)
        if thumbnail is None:
            self._thumbs[key] = thumbnail = Thumbnail(self.image(), size)
        return thumbnail

    def upload(self, stream):
        f = self.blobfile.open('w')
        size = upload_stream(stream, f)
        f.close()
        self.size = size

def upload_stream(stream, file):
    size = 0
    while 1:
        data = stream.read(1<<21)
        if not data:
            break
        size += len(data)
        file.write(data)
    return size

class Thumbnail(Persistent):
    mimetype = 'image/jpeg'

    def __init__(self, image, max_size):
        thumb_size = _thumb_size(image.size, max_size)
        thumb_img = image.resize(thumb_size, PIL.Image.ANTIALIAS)
        img_buf = StringIO()
        if thumb_img.mode != 'RGB':
            thumb_img = thumb_img.convert('RGB')
        thumb_img.save(img_buf, 'JPEG', quality=90)

        data = img_buf.getvalue()
        self.size = len(data)
        self.blobfile = blob = Blob()
        blob.open('w').write(data)
        self.image_size = thumb_img.size

    def image(self):
        return PIL.Image.open(self.blobfile.open())

def _thumb_size(orig_size, max_size):
    orig_x, orig_y = orig_size
    max_x, max_y = max_size

    x = max_x
    ratio = float(max_x) / float(orig_x)
    y = int(orig_y * ratio)

    if y <= max_y:
        return x, y

    y = max_y
    ratio = float(max_y) / float(orig_y)
    x = int(orig_x * ratio)

    assert x < max_x
    return x, y

class FilesToolFactory(ToolFactory):
    implements(IToolFactory)
    name = 'files'
    interfaces = (ICommunityRootFolder, ICommunityFolder, ICommunityFile)
    def add(self, context, request):
        files = create_content(ICommunityRootFolder)
        context['files'] = files

    def remove(self, context, request):
        del context['files']

files_tool_factory = FilesToolFactory()
