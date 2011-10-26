# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz.org
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

from htmllaundry import sanitize
from htmllaundry.cleaners import CommentCleaner, DocumentCleaner

def safe_html(text):
    """
    Take raw html and sanitize for safe use with tal:content="structure:x"
    """
    return sanitize(text,CommentCleaner)

def safe_body_html(text):
    """
    Take raw html and sanitize for safe use with tal:content="structure:x"
    """
    return sanitize(text,DocumentCleaner)

class ValidationError(Exception):
    '''
    Exception raised in views for validation errors.
    '''
    # XXX - please don't use this for any new code!
    def __init__(self, controller, **errors):
        self.errors = errors
        self.controller = controller

    def __str__(self):
        return '<ValidationError:%s>' % self.errors

def validation_error_handler(exc, request):
    '''
    General view handler setup for ValidationErrors that sets
    form errors and callbacks to the controllers make_response. 
    @param exc: ValidationError
    @param request: Request
    '''
    # XXX - please don't use this for any new code!
    controller = exc.controller
    form_errors = exc.errors  
    controller.api.formerrors.update(form_errors)
    return exc.controller.make_response()
