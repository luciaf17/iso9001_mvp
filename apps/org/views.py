from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.core.models import Process, Site

@login_required
def process_map(request):
	selected_site_id = request.GET.get("site_id")
	selected_type = request.GET.get("process_type")

	processes = Process.objects.filter(level=Process.Level.PROCESS).order_by("code")

	site_filter_id = None
	if selected_site_id:
		try:
			site_filter_id = int(selected_site_id)
		except (TypeError, ValueError):
			selected_site_id = ""

	if site_filter_id is not None:
		processes = processes.filter(site_id=site_filter_id)

	if selected_type:
		if selected_type in Process.ProcessType.values:
			processes = processes.filter(process_type=selected_type)
		else:
			selected_type = ""

	processes = processes.prefetch_related("children__children")
	sites = Site.objects.filter(is_active=True)

	context = {
		"processes": processes,
		"sites": sites,
		"selected_site_id": selected_site_id,
		"selected_type": selected_type,
		"types": Process.ProcessType.choices,
	}

	return render(request, "org/process_map.html", context)
