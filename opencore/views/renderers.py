from repoze.bfg.compat import json

def jsonp_renderer_factory(name):
    """ Configure this factory under the name `.jsonp` so that the
        callback can be defined before the suffix.
    """
    def _render(value, system):
        request = system.get('request')
        callback_key = 'callback'
        callback = None
        if request is not None:
            if not hasattr(request, 'response_content_type'):
                request.response_content_type = 'application/json'
            if 'jsonp_callback_key' in request.params:
                callback_key = request.params['jsonp_callback_key']

            callback = request.params.get(callback_key)

        res = json.dumps(value)
        if callback:
            res = '%s(%s)' % (callback, res)
        return res
    return _render
