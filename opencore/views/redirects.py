from webob.exc import HTTPFound
from repoze.bfg.url import model_url

def redirect_up_view(context, request):
    location = model_url(context.__parent__, request)
    return HTTPFound(location=location)

def redirect_favicon(context, request):
    api = request.api
    location = '%s/images/favicon.ico' % api.static_url
    return HTTPFound(location=location)

def redirect_rss_view_xml(context, request):
    location = model_url(context, request, 'atom.xml')
    return HTTPFound(location=location)
