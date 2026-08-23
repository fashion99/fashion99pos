from django.shortcuts import redirect


class RequireAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public_paths = {
            '/login/',
        }
        is_public_path = request.path in public_paths or request.path.startswith('/static/')

        if not request.user.is_authenticated and not is_public_path:
            return redirect('login')

        return self.get_response(request)