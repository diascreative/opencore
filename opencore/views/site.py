"""Publish static resources under /static/"""

import os
import re

from webob.exc import HTTPFound

from repoze.bfg.url import model_url
from repoze.bfg.view import static

from opencore.views.utils import get_user_home
from opencore.views.api import TemplateAPI
import logging

log = logging.getLogger(__name__) 

here = os.path.abspath(os.path.dirname(__file__))

# five year expires time
static_view = static('static', cache_max_age=157680000)

version_match = re.compile(r'^r-?\d+$').match
# version number is "r" plus an integer (possibly negative)

def versioning_static_view(context, request):
    # if the first element in the subpath is the version number, strip
    # it out of the subpath (see views/api.py static_url)
    subpath = request.subpath
    if subpath and version_match(subpath[0]):
        request.subpath = subpath[1:]
    return static_view(context, request)

def site_view(context, request):
    home, extra_path = get_user_home(context, request)
    location=model_url(home, request, *extra_path)
    log.info('site_view location=%s' % location)
    return HTTPFound(location=model_url(home, request, *extra_path))

class StaticRootFactory(object):
    def __init__(self, environ):
        pass



   