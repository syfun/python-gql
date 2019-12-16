from django.http.response import JsonResponse


class Response(JsonResponse):
    def __init__(self, data, **kwargs):
        json_dumps_params = kwargs.get('json_dumps_params', {})
        json_dumps_params['separators'] = (',', ':')
        kwargs['json_dumps_params'] = json_dumps_params
        super().__init__(data, **kwargs)
