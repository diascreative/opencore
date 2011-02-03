from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.security import authenticated_userid
from repoze.bfg.security import effective_principals
from repoze.bfg.security import has_permission
from repoze.bfg.url import model_url
from zope.component import getMultiAdapter

from opencore.consts import countries
from opencore.interfaces import ICatalogSearch
from opencore.interfaces import IGridEntryInfo
from opencore.interfaces import IContent
from opencore.interfaces import IProfile
from opencore.utilities.image import thumb_url
from opencore.utils import find_communities
from opencore.utils import find_tags
from opencore.utils import find_users
from opencore.utils import get_layout_provider
from opencore.utils import get_setting

from opencore.views.api import xhtml

'''from karl.views.batch import get_catalog_batch
from karl.views.login import logout_view
from karl.views.resetpassword import request_password_reset
from karl.views.utils import Invalid
from karl.views.utils import handle_photo_upload
from karl.views.utils import photo_from_filestore_view
from karl.views.forms import widgets as karlwidgets
from karl.views.forms import validators as karlvalidators
from karl.views.forms.filestore import get_filestore'''
from opencore.views.communities import get_preferred_communities
from opencore.views.communities import get_my_communities
from opencore.views.tags import get_tags_client_data
from opencore.views.utils import convert_to_script
from opencore.views.api import TemplateAPI
from opencore.utilities.image import thumb_url


PROFILE_THUMB_SIZE = (75, 100)

_MIN_PW_LENGTH = None

def min_pw_length():
    global _MIN_PW_LENGTH
    if _MIN_PW_LENGTH is None:
        _MIN_PW_LENGTH = get_setting(None, 'min_pw_length', 8)
    return _MIN_PW_LENGTH


def show_profile_view(context, request):
    """Show a profile with actions if the current user"""
    page_title = 'View Profile'
    api = TemplateAPI(context, request, page_title)

    # Create display values from model object
    profile = {}
    for name in [name for name in context.__dict__.keys()
                 if not name.startswith("_")]:
        profile_value = getattr(context, name)
        if profile_value is not None:
            # Don't produce u'None'
            profile[name] = unicode(profile_value)
        else:
            profile[name] = None

    if 'fax' not in profile:
        profile['fax'] = '' # BBB

    # 'websites' is a property, so the loop above misses it
    profile["websites"] = context.websites

    # ditto for 'title'
    profile["title"] = context.title

    if profile.has_key("languages"):
        profile["languages"] = context.languages

    if profile.has_key("department"):
        profile["department"] = context.department

    if profile.get("last_login_time"):
        stamp = context.last_login_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        profile["last_login_time"] = stamp

    if profile.has_key("country"):
        # translate from country code to country name
        country_code = profile["country"]
        country = countries.as_dict.get(country_code, u'')
        profile["country"] = country

    # Display portrait
    photo = context.get('photo')
    display_photo = {}
    if photo is not None:
        display_photo["url"] = api.static_url + thumb_url(photo, request, PROFILE_THUMB_SIZE)
    else:
        display_photo["url"] = api.static_url + "/images/defaultUser.gif"
    profile["photo"] = display_photo

    # provide client data for rendering current tags in the tagbox
    client_json_data = dict(
        tagbox = get_tags_client_data(context, request),
        )

    # Get communities this user is a member of, along with moderator info
    #
    communities = {}
    communities_folder = find_communities(context)
    user_info = find_users(context).get_by_id(context.__name__)
    if user_info is not None:
        for group in user_info["groups"]:
            if group.startswith("group.community:"):
                unused, community_name, role = group.split(":")
                if (communities.has_key(community_name) and
                    role != "moderators"):
                    continue

                community = communities_folder.get(community_name, None)
                if community is None:
                    continue

                if has_permission('view', community, request):
                    communities[community_name] = {
                        "title": community.title,
                        "moderator": role == "moderators",
                        "url": model_url(community, request),
                    }

    communities = communities.values()
    communities.sort(key=lambda x:x["title"])

    preferred_communities = []
    my_communities = None
    name = context.__name__
    # is this the current user's profile?
    if authenticated_userid(request) == name:
        preferred_communities = get_preferred_communities(communities_folder,
                                                          request)
        my_communities = get_my_communities(communities_folder, request)

    tagger = find_tags(context)
    if tagger is None:
        tags = ()
    else:
        tags = []
        names = tagger.getTags(users=[context.__name__])
        for name, count in sorted(tagger.getFrequency(names,
                                                      user=context.__name__),
                                  key=lambda x: x[1],
                                  reverse=True,
                                 )[:10]:
            tags.append({'name': name, 'count': count})

    # List recently added content
    num, docids, resolver = ICatalogSearch(context)(
        sort_index='creation_date', reverse=True,
        interfaces=[IContent], limit=5, creator=context.__name__,
        allowed={'query': effective_principals(request), 'operator': 'or'},
        )
    recent_items = []
    for docid in docids:
        item = resolver(docid)
        if item is None:
            continue
        adapted = getMultiAdapter((item, request), IGridEntryInfo)
        recent_items.append(adapted)

    return render_template_to_response(
        'templates/profile.pt',
        api=api,
        profile=profile,
        actions=get_profile_actions(context, request),
        photo=photo,
        head_data=convert_to_script(client_json_data),
        communities=communities,
        my_communities=my_communities,
        preferred_communities=preferred_communities,
        tags=tags,
        recent_items=recent_items,
        )

def profile_thumbnail(context, request):
    api = TemplateAPI(context, request, 'Profile thumbnail redirector')
    photo = context.get('photo')
    if photo is not None:
        url = thumb_url(photo, request, PROFILE_THUMB_SIZE)
    else:
        url = api.static_url + "/images/defaultUser.gif"
    return HTTPFound(location=url)

def get_profile_actions(profile, request):
    actions = []
    same_user = (authenticated_userid(request) == profile.__name__)
    if has_permission('administer', profile, request):
        actions.append(('Edit', 'admin_edit_profile.html'))
    elif same_user:
        actions.append(('Edit', 'edit_profile.html'))
    if same_user:
        actions.append(('Manage Communities', 'manage_communities.html'))
        actions.append(('Manage Tags', 'manage_tags.html'))
    return actions