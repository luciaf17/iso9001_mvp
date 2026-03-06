from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.models import Organization, Process, Site
from apps.core.services import log_audit_event
from apps.org.forms import ProcessForm
from apps.org.utils import can_edit_processes

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
		"can_edit": can_edit_processes(request.user),
	}

	if request.headers.get("HX-Request") == "true":
		return render(request, "org/partials/process_map_results.html", context)

	return render(request, "org/process_map.html", context)


@login_required
def process_create_level1(request):
	if not can_edit_processes(request.user):
		messages.error(request, "No tiene permisos para editar procesos.")
		return redirect("org:process_map")

	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("org:process_map")

	site = (
		Site.objects.filter(organization=organization, is_active=True).first()
		or Site.objects.filter(organization=organization).first()
	)
	if site is None:
		messages.error(request, "No hay sitio activo para la organizacion.")
		return redirect("org:process_map")

	form = ProcessForm(request.POST or None)
	form.instance.level = Process.Level.PROCESS
	form.instance.parent = None
	if request.method == "POST" and form.is_valid():
		process = form.save(commit=False)
		process.organization = organization
		process.site = site
		process.level = Process.Level.PROCESS
		process.parent = None
		process.save()
		log_audit_event(
			actor=request.user,
			action="org.process.created",
			instance=process,
			metadata={
				"process_id": process.id,
				"code": process.code,
				"name": process.name,
				"level": process.level,
				"process_type": process.process_type,
				"site_id": process.site_id,
				"is_active": process.is_active,
			},
			object_type_override="core.Process",
		)
		messages.success(request, "Proceso creado correctamente.")
		return redirect("org:process_map")

	return render(request, "org/process_form.html", {"form": form, "title": "Nuevo proceso"})


@login_required
def process_create_child(request, parent_id):
	if not can_edit_processes(request.user):
		messages.error(request, "No tiene permisos para editar procesos.")
		return redirect("org:process_map")

	parent = get_object_or_404(Process, id=parent_id)
	if parent.level == Process.Level.SECTOR:
		messages.error(request, "No se pueden crear hijos para un sector.")
		return redirect("org:process_map")

	child_level = (
		Process.Level.SUBPROCESS
		if parent.level == Process.Level.PROCESS
		else Process.Level.SECTOR
	)

	instance = Process(
		organization=parent.organization,
		site=parent.site,
		process_type=parent.process_type,
		level=child_level,
		parent=parent,
		is_active=True,
	)

	if request.method == "POST":
		data = request.POST.copy()
		data["process_type"] = parent.process_type
		form = ProcessForm(data, instance=instance)
	else:
		form = ProcessForm(
			initial={"process_type": parent.process_type, "is_active": True},
			instance=instance,
		)

	if request.method == "POST" and form.is_valid():
		sub_code = form.cleaned_data["code"]
		full_code = f"{parent.code}.{sub_code}"
		process = form.save(commit=False)
		process.code = full_code
		process.name = form.cleaned_data["name"]
		process.organization = parent.organization
		process.site = parent.site
		process.process_type = parent.process_type
		process.level = child_level
		process.parent = parent
		process.save()
		log_audit_event(
			actor=request.user,
			action="org.process.created",
			instance=process,
			metadata={
				"process_id": process.id,
				"code": process.code,
				"name": process.name,
				"level": process.level,
				"process_type": process.process_type,
				"parent_id": process.parent_id,
				"site_id": process.site_id,
				"is_active": process.is_active,
			},
			object_type_override="core.Process",
		)
		messages.success(request, "Proceso creado correctamente.")
		return redirect("org:process_map")

	return render(
		request,
		"org/process_form.html",
		{
			"form": form,
			"title": "Nuevo subproceso" if child_level == Process.Level.SUBPROCESS else "Nuevo sector",
			"parent": parent,
		},
	)


@login_required
def process_edit(request, process_id):
	if not can_edit_processes(request.user):
		messages.error(request, "No tiene permisos para editar procesos.")
		return redirect("org:process_map")

	process = get_object_or_404(Process, id=process_id)
	form = ProcessForm(request.POST or None, instance=process)
	form.fields["code"].disabled = True

	if request.method == "POST" and form.is_valid():
		updated = form.save(commit=False)
		updated.code = process.code
		updated.save()
		log_audit_event(
			actor=request.user,
			action="org.process.updated",
			instance=updated,
			metadata={
				"process_id": updated.id,
				"code": updated.code,
				"name": updated.name,
				"level": updated.level,
				"process_type": updated.process_type,
				"parent_id": updated.parent_id,
				"site_id": updated.site_id,
				"is_active": updated.is_active,
			},
			object_type_override="core.Process",
		)
		messages.success(request, "Proceso actualizado correctamente.")
		return redirect("org:process_map")

	return render(
		request,
		"org/process_form.html",
		{
			"form": form,
			"title": "Editar proceso",
			"process": process,
		},
	)


@login_required
def process_deactivate(request, process_id):
	if request.method != "POST":
		messages.error(request, "Metodo no permitido.")
		return redirect("org:process_map")

	if not can_edit_processes(request.user):
		messages.error(request, "No tiene permisos para desactivar procesos.")
		return redirect("org:process_map")

	process = get_object_or_404(Process, id=process_id)
	if process.children.filter(is_active=True).exists():
		messages.error(request, "No se puede desactivar un proceso con hijos activos.")
		return redirect("org:process_map")

	process.is_active = False
	process.save()
	log_audit_event(
		actor=request.user,
		action="org.process.deactivated",
		instance=process,
		metadata={
			"process_id": process.id,
			"code": process.code,
			"name": process.name,
			"level": process.level,
			"process_type": process.process_type,
			"parent_id": process.parent_id,
			"site_id": process.site_id,
			"is_active": process.is_active,
		},
		object_type_override="core.Process",
	)
	messages.success(request, "Proceso desactivado correctamente.")
	return redirect("org:process_map")
