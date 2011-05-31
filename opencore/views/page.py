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
    
    return {'api': api, 'page': context,}  


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
