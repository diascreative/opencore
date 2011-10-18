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

import calendar
import copy
from asyncore import compact_traceback
from zope.component import queryAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility

from repoze.bfg.interfaces import ISettings
from repoze.bfg.traversal import find_root
from repoze.bfg.traversal import find_interface
from repoze.lemonade.content import get_content_type

from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import ICommunity
from opencore.models.interfaces import ISite
from opencore.models.interfaces import IAttachmentPolicy
from opencore.views.interfaces import IFolderAddables
from opencore.views.interfaces import ILayoutProvider

def find_site(context):
    site = find_interface(context, ISite)
    if site is None:
        # for unittesting convenience
        site = find_root(context)
    return site

def find_users(context):
    return getattr(find_site(context), 'users', None)

def find_catalog(context):
    return getattr(find_site(context), 'catalog', None)

def find_events(context):
    return getattr(find_site(context), 'events', None)

def find_tags(context):
    return getattr(find_site(context), 'tags', None)

def find_profiles(context):
    return find_site(context).get('profiles')

def find_community(context):
    return find_interface(context, ICommunity)

def find_communities(context):
    site = find_site(context)
    return site.get(site.communities_name)


def get_setting(context, setting_name, default=None):
    # Grab a setting from ISettings.  (context is ignored.)
    settings = queryUtility(ISettings)
    return getattr(settings, setting_name, default)

def get_content_type_name(resource):
    content_iface = get_content_type(resource)
    return content_iface.getTaggedValue('name')

def get_session(context, request):
    site = find_site(context)
    session = site.sessions.get(request.environ['repoze.browserid'])
    return session

_MAX_32BIT_INT = int((1<<31) - 1)

def docid_to_hex(docid):
    return '%08X' % (_MAX_32BIT_INT + docid)

def hex_to_docid(hex):
    return int('%s' % hex, 16) - _MAX_32BIT_INT

def asbool(s):
    s = str(s).strip()
    return s.lower() in ('t', 'true', 'y', 'yes', 'on', '1')

def coarse_datetime_repr(date):
    """Convert a datetime to an integer with 100 second granularity.

    The granularity reduces the number of index entries in the
    catalog.
    """
    timetime = calendar.timegm(date.timetuple())
    return int(timetime) // 100

def support_attachments(context):
    """Return true if the given object should support attachments"""
    adapter = queryAdapter(context, IAttachmentPolicy)
    if adapter:
        return adapter.support()
    else:
        # support attachments by default
        return True

class PersistentBBB(object):
    """ A descriptor which fixes up old persistent instances with a
    default value as a 'write on read' operation.  This is usually not
    useful if the default value isn't mutable, and arguably 'write on
    read' behavior is evil.  Note that this descriptor returns the
    value after *replacing itself* on the instance with the value."""
    def __init__(self, name, val):
        self.name = name
        self.val = val

    def __get__(self, inst, cls):
        setattr(inst, self.name, copy.deepcopy(self.val))
        return getattr(inst, self.name)

def get_layout_provider(context, request):
    from opencore.views.adapters import DefaultLayoutProvider
    return queryMultiAdapter((context, request), ILayoutProvider,
                             default=DefaultLayoutProvider(context,request))

def get_folder_addables(context, request):
    from opencore.views.adapters import DefaultFolderAddables
    return queryMultiAdapter((context, request), IFolderAddables,
                             default=DefaultFolderAddables(context,request))

def find_tempfolder(context):
    root = find_root(context)
    if not 'TEMP' in root:
        root['TEMP'] = TempFolder()
    return root['TEMP']

def get_user_bookmarks(context, userid, filter_community=True):
    search = ICatalogSearch(context)
    num, docids, resolver = search(bookmarks=[userid])
    listings = [ l for l in [resolver(docid) for docid in docids] \
                        if userid in l.get('bookmarks', []) ] # thanks catalog!

    if filter_community:
        community = find_community(context)
        listings = [l for l in listings if community == find_community(l) ]

    return listings

def debugsearch(context, **kw):
    searcher = ICatalogSearch(context)
    kw['use_cache'] = False
    num, docids, resolver = searcher(**kw)
    L = []
    for docid in docids:
        L.append(resolver(docid))
    return num, L

def query_count(context, **kw):
    searcher = ICatalogSearch(context)
    total, docids, resolver = searcher(**kw)  
    return total 

def list_indexes(context):
    from opencore.tagging.index import TagIndex
    from repoze.catalog.indexes.text import CatalogTextIndex
    from repoze.bfg.traversal import find_model
    
    catalog = find_catalog(context)
    for name, index in catalog.items():
        try:
            if isinstance(index, TagIndex):
                tags = find_site(context).tags
                taglist = list(tags._tagid_to_obj.items())
                print name, (len(taglist), taglist)
            elif isinstance(index, CatalogTextIndex):    
                docids = index.index._docwords
                objs = []
                for docid in docids:
                   path = catalog.document_map.address_for_docid(docid)
                   context = find_model(context, path)
                   objs.append(context)
                print name, (len(objs), objs)   
            else:    
                print name, list_index(index)
        except Exception, e:
            print e    

def list_index(index):
    index_keys = list(index._fwd_index.keys())
    return len(index_keys), index_keys
            
def find_supported_interface(context, class_or_interfaces):
    '''
    Finds the first supported interface navigating up the tree from context until an interface is matched.
    Returns None if a match is not found.
    @param context: locatable content object
    @param class_or_interfaces: list of interfaces 
    '''
    found = None
    for class_or_interface in class_or_interfaces:
        found = find_interface(context, class_or_interface)
        if found: 
            return found    
    return found 


def fetch_url(url, data=None, timeout=None,  httpDebugLevel=0):
    import urllib2
    import socket
    from urllib2 import Request
    errorMessage = ""
    # best to make out we are a browser
    userAgent = 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322)'
    httpHeaders = {
            'User-agent' : userAgent,
            'Proxy-Connection' : 'Keep-Alive',
            'Accept-Encoding' : 'gzip, deflate',
            'Pragma' : 'no-cache',
            'Cache-Control' : 'no-cache',
            'Connection' : 'Keep-Alive'
    }
    try:
        httpLogger = urllib2.HTTPHandler(debuglevel=httpDebugLevel)
        if timeout:
            socket.setdefaulttimeout(timeout)
        opener = urllib2.build_opener(httpLogger)
        request = None
        if data:
            request = Request(url, data=data, headers=httpHeaders)
        else:
            request = Request(url, headers=httpHeaders)
        response =  opener.open(request)
        return response.read(), response.headers

    except urllib2.HTTPError, e:
        errorMessage = 'Could not get file for '+ url + '. Exception: ' + str(e)
    except urllib2.URLError, e:
        errorMessage = 'Failed to reach server. Exception: ' + str(e)
    except IOError, e:
        errorMessage = 'IOError Exception: ' + str(e)
    except socket.error:
        errno, errstr = sys.exc_info()[:2]
        if errno == socket.timeout:
            errorMessage = 'Socket timeout getting ' + url + ':' + str(errstr)
        else:
            errorMessage = 'Some socket error ' + url + ':' + str(errstr)
    except Exception, e:
        errorMessage = 'Exception:' + str(e) + ', for url=' + url
    raise ValueError('Exception during fetch_url, exception=%s' % errorMessage)    
