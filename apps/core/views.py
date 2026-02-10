from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.shortcuts import render


@login_required
def home(request):
	return render(request, "home.html")


class LogoutAllowGetView(LogoutView):
	http_method_names = ["get", "post", "head", "options"]
