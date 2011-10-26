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

from repoze.bfg.chameleon_zpt import render_template_to_response

from colander import (
        MappingSchema,
        SchemaNode,
        String,
        )
from deform.widget import RichTextWidget

from opencore.views.forms import ContentController

class PageSchema(MappingSchema):
    
    title = SchemaNode(
        String(),
        )

    text = SchemaNode(
        String(),
        widget=RichTextWidget(),
        )

def show_page(context, request):
    api = request.api
    template = getattr(context, 'template', 'page.pt')
    result = render_template_to_response("templates/" + template, api=api,
            page=context)
    return result


class EditPageController(ContentController):
    
    def __init__(self, context, request):
        super(EditPageController,self).__init__(context,request)
        self.api.page_title = 'Edit %s' % self.context.title
        self.Schema = PageSchema

    def form_defaults(self):
        context = self.context

        defaults = { 'title': context.title, 'text': context.text, }

        return defaults

    def handle_content(self, context, request, validated):
        context.title = validated['title']
        context.text = validated['text']
