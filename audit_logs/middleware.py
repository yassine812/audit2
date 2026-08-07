import threading

_thread_locals = threading.local()


def get_current_user():
    """Retourne l'utilisateur actuellement connecté pour le thread courant."""
    return getattr(_thread_locals, "user", None)


class CurrentUserMiddleware:
    """Middleware enregistrant l'utilisateur courant dans un stockage local au thread."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, "user", None)
        try:
            response = self.get_response(request)
        finally:
            _thread_locals.user = None
        return response
