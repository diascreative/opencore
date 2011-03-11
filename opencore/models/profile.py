from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from persistent import Persistent
from BTrees.OOBTree import OOBTree
from zope.interface import implementer
from zope.interface import implements
from zope.component import adapter

from repoze.folder import Folder
from opencore.consts import countries
from opencore.models.interfaces import IProfile
from opencore.models.interfaces import IProfiles
from opencore.models.interfaces import ITextIndexData
from opencore.models.interfaces import IPeopleCategory
from opencore.models.interfaces import IPeopleCategoryItem
from opencore.models.interfaces import ISocial


class Profile(Folder):

    implements(IProfile)

    alert_attachments = 'link'
   
    def __init__(self,
                 firstname = '',
                 lastname = '',
                 email = '',
                 phone = '',
                 extension = '',
                 fax = '',
                 department = '',
                 position = '',
                 organization = '',
                 location = '',
                 country = '',
                 websites = None,
                 languages = '',
                 office='',
                 room_no='',
                 biography='',
                 data=None,
                 home_path=None,
                 preferred_communities = None,
                 dob = None,
                 gender = ''
                ):
        super(Profile, self).__init__(data)
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.phone = phone
        self.fax = fax
        self.extension = extension
        self.department = department
        self.position = position
        self.organization = organization
        self.location = location
        if country not in countries.as_dict:
            country = 'XX'
        self.country = country
        self.websites = websites or ()
        self.languages = languages
        self.office = office
        self.room_no = room_no
        self.biography = biography
        self.home_path = home_path
        self._alert_prefs = PersistentMapping()
        self._pending_alerts = PersistentList()
        self.categories = PersistentMapping()
        self.password_reset_key = None
        self.password_reset_time = None
        self.preferred_communities = preferred_communities
        self.last_login_time = None
        # states are 
        # 1. inactive - user has become inactive rather than deleted from the system. 
        # 2. active   - registered with a invite email which creates the profile
        self.security_state = 'active'
        self.dob = dob
        self.gender = gender

    @property
    def creator(self):
        return self.__name__

    @property
    def title(self):
        title = [self.firstname.strip(), self.lastname.strip()]
        if getattr(self, 'security_state', None) == 'inactive':
            title += ['(Inactive)',]
        return unicode(' '.join(title))

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

class CaseInsensitiveOOBTree(OOBTree):
    def __getitem__(self, name):
        return super(CaseInsensitiveOOBTree, self).__getitem__(name.lower())

    def __setitem__(self, name, value):
        return super(CaseInsensitiveOOBTree, self).__setitem__(name.lower(),
                                                               value)
    def get(self, name, default=None):
        return super(CaseInsensitiveOOBTree, self).get(name.lower(), default)

class ProfilesFolder(Folder):

    implements(IProfiles)

    def __init__(self, data=None):
        super(ProfilesFolder, self).__init__(data)
        self.email_to_name = CaseInsensitiveOOBTree()

    def getProfileByEmail(self, email):
        name = self.email_to_name.get(email)
        if name is not None:
            return self[name]

@implementer(ITextIndexData)
@adapter(IProfile)
def profile_textindexdata(profile):
    """Provides info for the text index"""
    text = []
    for attr in (
        '__name__',
        "firstname",
        "lastname",
        "email",
        "phone",
        "extension",
        "department",
        "position",
        "organization",
        "location",
        "country",
        "website",
        "languages",
        "office",
        "room_no",
        "biography",
        ):
        v = getattr(profile, attr, None)
        if v:
            if isinstance(v, str):
                try:
                    v = v.decode('UTF8')
                except UnicodeDecodeError:
                    v = v.decode('latin1')
            text.append(unicode(v))
    text = '\n'.join(text)
    return lambda: text

class ProfileCategoryGetter:
    """Gets category values from profiles.

    Limited to a particular category key.
    """

    def __init__(self, catid):
        self.catid = catid

    def __call__(self, obj, default):
        if not IProfile.providedBy(obj):
            return default
        categories = getattr(obj, 'categories', None)
        if not categories:
            return default
        values = categories.get(self.catid)
        if not values:
            return default
        return values

social_category =  ProfileCategoryGetter('social')
   
class PeopleCategory(Folder):
    implements(IPeopleCategory)
    is_ordered = False

    def __init__(self, title):
        super(PeopleCategory, self).__init__()
        self.title = title


class PeopleCategoryItem(Persistent):
    implements(IPeopleCategoryItem)
    is_ordered = False
    sync_id = None # normally set by GSA sync.

    def __init__(self, title, description=u''):
        self.title = title
        self.description = description  # HTML blob    
        

class SocialPeopleCategoryItem(PeopleCategoryItem):
    implements(ISocial)
    
    def __init__(self, id, title, description=u''):
        PeopleCategoryItem.__init__(self, title, description)
        self.id = id    
