def show_page(context, request):
    api = request.api
    
    return {'api': api, 'page': context,}  
