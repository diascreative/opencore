from repoze.bfg.url import model_url

class ToolFactory(object):
    name = None
    interfaces = ()
    def add(self, context, request):
        raise NotImplementedError

    def remove(self, context, request):
        raise NotImplementedError

    def is_present(self, context, request):
        if self.name is None:
            raise NotImplementedError
        return self.name in context

    def is_current(self, context, request):
        if not self.interfaces:
            raise NotImplementedError
        for iface in self.interfaces:
            if iface.providedBy(request.context):
                return True
        return False

    def tab_url(self, context, request):
        if not self.name:
            raise NotImplementedError
        return model_url(context, request, self.name)
    
