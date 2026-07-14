from django.utils.http import url_has_allowed_host_and_scheme


class RedirectBackMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method != 'POST':
            return response

        next_url = (request.POST.get('next') or '').strip()
        if not next_url:
            return response

        # Compat: éviter HttpResponseRedirectBase (pas présent selon version Django)
        # On détecte une redirection via le status code + header Location.
        if getattr(response, 'status_code', None) not in (301, 302, 303, 307, 308):
            return response

        if not getattr(response, 'has_header', None) or not response.has_header('Location'):
            return response

        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return response

        response['Location'] = next_url
        return response
