from django.http import HttpResponse

class BlockChromeDevtoolsWellKnown:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        if request.path == "/.well-known/appspecific/com.chrome.devtools.json":
            resp = HttpResponse(status=204)
            resp["Cache-Control"] = "public, max-age=86400"
            return resp
        return self.get_response(request)
