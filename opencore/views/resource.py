"""Views registered to multiple content types.
"""

from repoze.bfg.url import model_url
from webob.exc import HTTPFound

from opencore.utils import find_community
from opencore.utils import get_layout_provider
from opencore.views.api import TemplateAPI

def delete_resource_view(context, request, num_children=0):

    page_title = 'Delete ' + context.title
    api = TemplateAPI(context, request, page_title)

    confirm = request.params.get('confirm')
    if confirm:
        location = model_url(
            context.__parent__, request,
            query=dict(status_message= 'Deleted %s' % context.title)
            )
        del context.__parent__[context.__name__]
        return HTTPFound(location=location)

    # Get a layout
    layout_provider = get_layout_provider(context, request)
    layout_name = 'generic'
    if find_community(context):
        layout_name = 'community'
    layout = layout_provider(layout_name)

    return {'api': api,
            'layout': layout,
            'num_children': num_children,
           }

