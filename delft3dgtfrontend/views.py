from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


@login_required
def home(request):
	return HttpResponse('success')
