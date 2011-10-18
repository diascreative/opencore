# Copyright (C) 2008-2009 Open Society Institute
#               !!! The original copyright holder !!!
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

from cStringIO import StringIO

from zope.interface import implements
from zope.interface import Interface

from repoze.bfg.testing import DummyModel
from repoze.bfg.testing import registerAdapter
from repoze.bfg.testing import registerDummyRenderer
from repoze.bfg.testing import registerUtility

from opencore.models.interfaces import (
        ICommunity,
        IProfile, 
        IImage,
        )

from opencore.views.forms import tmpstore

class DummyImageModel(DummyModel):
    implements(IImage)

class DummyCatalog(dict):
    def __init__(self, *maps):
        self.document_map = DummyDocumentMap(*maps)
        self.queries = []
        self.indexed = []
        self.unindexed = []
        self.reindexed = []
        self.maps = list(maps)

    def index_doc(self, docid, object):
        self.indexed.append(object)

    def unindex_doc(self, docid):
        self.unindexed.append(docid)

    def reindex_doc(self, docid, object):
        self.reindexed.append(object)

    def search(self, **kw):
        self.queries.append(kw)
        try:
            result = self.maps.pop(0)
        except IndexError:
            return 0, ()
        result = sorted(result.keys())
        return len(result), result

class DummyDocumentMap:
    def __init__(self, *maps):
        self.added = []
        self.removed = []
        self.maps = list(maps)

    def add(self, path, docid=None):
        self.added.append((docid, path))
        return 1

    def docid_for_address(self, path):
        for docid, spath in self.added:
            if path == spath:
                return docid

        for map in self.maps:
            for docid, spath in map.items():
                if path == spath:
                    return docid

    def address_for_docid(self, docid):
        for sdocid, path in self.added:
            if sdocid == docid:
                return path

        for map in self.maps:
            for sdocid, path in map.items():
                if sdocid == docid:
                    return path

    def remove_docid(self, docid):
        self.removed.append(docid)

class DummyProfile(DummyModel):
    implements(IProfile)

    title = 'title'
    firstname = 'firstname'
    biography = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'
    lastname = 'lastname'
    position = 'position'
    organization = 'organization'
    phone = 'phone'
    extension = 'extension'
    fax = 'fax'
    department = 'department1'
    location = 'location'
    alert_attachments = 'link'
    country = 'country'

    def __init__(self, *args, **kw):
        DummyModel.__init__(self)
        for item in kw.items():
            setattr(self, item[0], item[1])
        self._alert_prefs = {}
        self._pending_alerts = []
        if 'security_state' not in kw:
            self.security_state = 'active'
      
    @property
    def creator(self):
        return self.__name__
    
    @property
    def email(self):
        return "%s@x.org" % self.__name__

    def get_alerts_preference(self, community_name):
        return self._alert_prefs.get(community_name,
                                     IProfile.ALERT_IMMEDIATELY)

    def set_alerts_preference(self, community_name, preference):
        if preference not in (
            IProfile.ALERT_IMMEDIATELY,
            IProfile.ALERT_DIGEST,
            IProfile.ALERT_NEVER):
            raise ValueError("Invalid preference.")

        self._alert_prefs[community_name] = preference

class DummyRoot(DummyModel):
    def __init__(self):
        DummyModel.__init__(self)
        self[u'profiles'] = DummyModel()
        dummies = [
            (u'dummy1', u'Dummy One'),
            (u'dummy2', u'Dummy Two'),
            (u'dummy3', u'Dummy Three'),
            ]
        for dummy in dummies:
            self[u'profiles'][0] = DummyModel(title=dummy[1])
        self[u'communities'] = DummyModel()

class DummySettings(dict):
    reload_templates = True
    system_name = "karl3test"
    system_email_domain = "karl3.example.com"
    min_pw_length = 8
    admin_email = 'admin@example.com'
    staff_change_password_url = 'http://pw.example.com'
    forgot_password_url = 'http://login.example.com/resetpassword'
    offline_app_url = "http://offline.example.com/app"
    selectable_groups = 'group.KarlAdmin group.KarlLovers'

    def __init__(self, **kw):
        for k, v in self.__class__.__dict__.items():
            self[k] = v
        for k, v in kw.items():
            self[k] = v

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

class DummyAdapter:
    def __init__(self, context, request):
        self.context = context
        self.request = request

class DummyCommunity(DummyModel):
    implements(ICommunity)
    title = u'Dummy Communit\xe0'
    description = u'Dummy Description'

    def __init__(self):
        DummyModel.__init__(self)
        root = DummyRoot()
        root["communities"]["community"] = self

class DummyMailer(list):
    class DummyMessage(object):
        def __init__(self, mfrom, mto, msg):
            self.mfrom = mfrom
            self.mto = mto
            self.msg = msg

            from email.message import Message
            assert isinstance(msg, Message), type(msg)

    def send(self, mfrom, mto, msg):
        self.append(self.DummyMessage(mfrom, mto, msg))

def registerDummyMailer():
    from repoze.bfg.testing import registerUtility
    from repoze.sendmail.interfaces import IMailDelivery
    mailer = DummyMailer()
    registerUtility(mailer, IMailDelivery)
    return mailer

class DummyFile:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.size = 0

class DummyUsers:
    def __init__(self, community=None, encrypt=None):
        self.removed_users = []
        self.removed_groups = []
        self.added_groups = []
        self.community = community
        self._by_id = {}
        self._by_login = {}
        if encrypt is None:
            encrypt = lambda password: password
        self.encrypt = encrypt

    def add(self, userid, login, password, groups, encrypted=False):
        if not encrypted:
            password = self.encrypt(password)
        self.added = (userid, login, password, groups)
        userinfo = {
            "id": userid,
            "login": login,
            "password": password,
            "groups": groups,
            }
        self._by_login[login] = userinfo
        self._by_id[userid] = userinfo

        if (self.community is not None and
            hasattr(self.community, "moderators_group_name") and
            hasattr(self.community, "members_group_name")):
            for group_name in groups:
                if group_name == self.community.moderators_group_name:
                    self.community.moderator_names.add(userid)
                elif group_name == self.community.members_group_name:
                    self.community.member_names.add(userid)

    def remove(self, userid):
        self.removed_users.append(userid)

    def add_user_to_group(self, userid, group_name):
        self.added_groups.append((userid, group_name))
        if (self.community is not None and
            hasattr(self.community, "moderators_group_name") and
            hasattr(self.community, "members_group_name")):
            if group_name == self.community.moderators_group_name:
                self.community.moderator_names.add(userid)
            elif group_name == self.community.members_group_name:
                self.community.member_names.add(userid)
    add_group = add_user_to_group

    def remove_user_from_group(self, userid, group_name):
        self.removed_groups.append((userid, group_name))

        if (self.community is not None and
            hasattr(self.community, "moderators_group_name") and
            hasattr(self.community, "members_group_name")):
            if group_name == self.community.moderators_group_name:
                self.community.moderator_names.remove(userid)
            elif group_name == self.community.members_group_name:
                if userid in self.community.member_names:
                    self.community.member_names.remove(userid)
    remove_group = remove_user_from_group

    def get_by_id(self, userid):
        if self._by_id.has_key(userid):
            return self._by_id[userid]
        return None

    def get_by_login(self, login):
        if self._by_login.has_key(login):
            return self._by_login[login]
        return None

    def get(self, userid=None, login=None):
        if userid is not None:
            return self.get_by_id(userid)
        else:
            return self.get_by_login(login)

    def change_password(self, userid, password):
        from repoze.who.plugins.zodb.users import get_sha_password
        self._by_id[userid]["password"] = get_sha_password(password)

    def change_login(self, userid, new_login):
        if new_login == 'raise_value_error':
            raise ValueError, 'This is the error message.'
        user = self._by_id[userid]
        del self._by_login[user['login']]
        self._by_login[new_login] = user
        user['login'] = new_login

    def member_of_group(self, userid, group):
        if userid in self._by_id:
            return group in self._by_id[userid]['groups']
        return False

    def users_in_group(self, group):
        return [id for id in self._by_id if group in self._by_id[id]['groups']]

class DummyUpload(object):
    """Simulates an HTTP upload.  Suitable for assigning as the value to
    to a dummy request form parameter.
    """
    def __init__(self, filename="test.txt",
                       mimetype="text/plain",
                       data="This is a test."):
        self.filename = filename
        self.type = mimetype
        self.mimetype = mimetype
        self.data = data
        self.file = StringIO(data)
        self.length = len(data)

one_pixel_jpeg = [
0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01,
0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xff, 0xdb, 0x00, 0x43, 0x00, 0x05,
0x03, 0x04, 0x04, 0x04, 0x03, 0x05, 0x04, 0x04, 0x04, 0x05, 0x05, 0x05, 0x06,
0x07, 0x0c, 0x08, 0x07, 0x07, 0x07, 0x07, 0x0f, 0x0b, 0x0b, 0x09, 0x0c, 0x11,
0x0f, 0x12, 0x12, 0x11, 0x0f, 0x11, 0x11, 0x13, 0x16, 0x1c, 0x17, 0x13, 0x14,
0x1a, 0x15, 0x11, 0x11, 0x18, 0x21, 0x18, 0x1a, 0x1d, 0x1d, 0x1f, 0x1f, 0x1f,
0x13, 0x17, 0x22, 0x24, 0x22, 0x1e, 0x24, 0x1c, 0x1e, 0x1f, 0x1e, 0xff, 0xdb,
0x00, 0x43, 0x01, 0x05, 0x05, 0x05, 0x07, 0x06, 0x07, 0x0e, 0x08, 0x08, 0x0e,
0x1e, 0x14, 0x11, 0x14, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0xff, 0xc0, 0x00, 0x11, 0x08, 0x00, 0x01, 0x00, 0x01, 0x03, 0x01,
0x22, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01, 0xff, 0xc4, 0x00, 0x15, 0x00,
0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x08, 0xff, 0xc4, 0x00, 0x14, 0x10, 0x01, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0xff, 0xc4, 0x00, 0x14, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xc4, 0x00,
0x14, 0x11, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xda, 0x00, 0x0c, 0x03, 0x01, 0x00,
0x02, 0x11, 0x03, 0x11, 0x00, 0x3f, 0x00, 0xb2, 0xc0, 0x07, 0xff, 0xd9
]

one_pixel_jpeg = ''.join([chr(x) for x in one_pixel_jpeg])

class DummyImageFile(object):
    implements(IImage)
    def __init__(self, title=None, stream=None, mimetype=None, filename=None,
                 creator=None, order=0):
        self.title = title
        self.mimetype = mimetype
        if stream is not None:
            self.data = stream.read()
        else:
            self.data = one_pixel_jpeg
        self.size = len(self.data)
        self.filename= filename
        self.creator = creator
        self.is_image = mimetype != 'x-application/not a jpeg'
        self.order = order

class DummySearchAdapter:
    def __init__(self, context):
        self.context = context

    def __call__(self, **kw):
        if kw.get('texts') == 'the':
            # simulate a text index parse exception
            from zope.index.text.parsetree import ParseError
            raise ParseError("Query contains only common words: 'the'")
        if kw.get('email') == ['match@x.org']:
            # simulate finding a match for an email address
            profile = DummyProfile(__name__='match')
            return 1, [1], [profile]
        return 0, [], None

class DummySearch(DummyModel):
    """
    A more generic DummySearch

    # use like:
    search = DummySearch(result1,result2)
    directlyProvides(search, ICatalogSearch)
    
    self.assertEqual(search.spec,
                     ...)
    """
    def __init__(self,*results):
        # results should be a sequence of objects
        self.results = results

    def resolve(self,docid):
        return self.results[docid]
    
    def __call__(self, *args, **kw):
        self.spec = (args,kw)
        return len(self.results), range(len(self.results)), self.resolve
    
class DummyTagQuery(DummyAdapter):
    tagswithcounts = []
    docid = 'ABCDEF01'

class DummyFolderAddables(DummyAdapter):
    def __init__(self, context, request):
        pass

    def __call__(self):
        return [
            ('Add Folder', 'add_folder.html'),
            ('Add File', 'add_file.html'),
            ]

class DummyFolderCustomizer(DummyAdapter):
    markers = []

class DummyLayoutProvider(DummyAdapter):
    template_fn = 'opencore.views:templates/community_layout.fn'

    def __call__(self, default):
        renderer = registerDummyRenderer(self.template_fn)
        return renderer

class DummyOrdering:
    _items = []

    def sync(self, entries):
        pass

    def moveUp(self, name):
        pass

    def moveDown(self, name):
        pass

    def add(self, name):
        pass

    def remove(self, name):
        pass

    def items(self):
        return []

    def previous_name(self, name):
        return u'previous1'

    def next_name(self, name):
        return u'next1'

class DummySessions(dict):
    def get(self, name, default=None):
        if name not in self:
            self[name] = {}
        return self[name]

def registerLayoutProvider():
    from opencore.views.interfaces import ILayoutProvider
    registerAdapter(DummyLayoutProvider,
                    (Interface, Interface),
                    ILayoutProvider)

def registerTagbox():
    from opencore.models.interfaces import ITagQuery
    registerAdapter(DummyTagQuery, (Interface, Interface),
                    ITagQuery)

def registerAddables():
    from opencore.views.interfaces import IFolderAddables
    registerAdapter(DummyFolderAddables, (Interface, Interface),
                    IFolderAddables)

def registerKarlDates():
    d1 = 'Wednesday, January 28, 2009 08:32 AM'
    def dummy(date, flavor):
        return d1
    from opencore.utilities.interfaces import IKarlDates
    registerUtility(dummy, IKarlDates)

def registerCatalogSearch():
    from opencore.models.interfaces import ICatalogSearch
    registerAdapter(DummySearchAdapter, (Interface, Interface),
                    ICatalogSearch)
    registerAdapter(DummySearchAdapter, (Interface,),
                    ICatalogSearch)

def registerSettings(**kw):
    from repoze.bfg.interfaces import ISettings
    settings = DummySettings(**kw)
    registerUtility(settings, ISettings)


def insert_in_tmpstore(key='store-key', filename='one_pixel.jpg'):
    data = {}
    data['fp'] = StringIO(one_pixel_jpeg)
    data['filename'] = filename
    data['mimetype'] = 'image/jpeg'
    data['size']  = len(one_pixel_jpeg)
    tmpstore[key] = data
