from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, render, get_object_or_404

from apps.core.forms import OrganizationContextForm, StakeholderForm
from apps.core.models import Organization, OrganizationContext, Site, Stakeholder, Process
from apps.core.services import log_audit_event
from apps.core.utils import can_edit_context, can_edit_stakeholders
from apps.docs.models import Document


@login_required
def home(request):
	return render(request, "home.html")


class LogoutAllowGetView(LogoutView):
	http_method_names = ["get", "post", "head", "options"]


@login_required
def context_detail(request):
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	context_obj, _ = OrganizationContext.objects.get_or_create(organization=organization)
	can_edit = can_edit_context(request.user)

	return render(
		request,
		"context/detail.html",
		{
			"context_obj": context_obj,
			"organization": organization,
			"can_edit": can_edit,
		},
	)


@login_required
def context_edit(request):
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	context_obj, _ = OrganizationContext.objects.get_or_create(organization=organization)
	can_edit = can_edit_context(request.user)
	if not can_edit:
		messages.error(request, "No tiene permisos para editar el contexto.")
		return redirect("core:context_detail")

	User = get_user_model()
	form = OrganizationContextForm(request.POST or None, instance=context_obj)
	form.fields["site"].queryset = Site.objects.filter(organization=organization, is_active=True)
	form.fields["owner"].queryset = User.objects.filter(is_active=True)
	form.fields["quality_policy_doc"].queryset = Document.objects.filter(is_active=True)
	form.fields["process_map_doc"].queryset = Document.objects.filter(is_active=True)
	form.fields["org_chart_doc"].queryset = Document.objects.filter(is_active=True)
	form.fields["context_analysis_doc"].queryset = Document.objects.filter(is_active=True)

	if request.method == "POST" and form.is_valid():
		context_obj = form.save()
		log_audit_event(
			actor=request.user,
			action="core.context.updated",
			instance=context_obj,
			metadata={
				"organization_id": organization.id,
				"site_id": context_obj.site_id,
			},
		)
		messages.success(request, "Contexto actualizado correctamente.")
		return redirect("core:context_detail")

	return render(
		request,
		"context/edit.html",
		{
			"form": form,
			"organization": organization,
			"context_obj": context_obj,
		},
	)


def _get_current_organization():
	return Organization.objects.filter(is_active=True).first() or Organization.objects.first()


def _configure_stakeholder_form(form, organization):
	form.fields["related_process"].queryset = Process.objects.filter(
		organization=organization,
		is_active=True,
	).order_by("code")
	form.fields["related_document"].queryset = Document.objects.filter(is_active=True)


@login_required
def stakeholder_list(request):
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	stakeholders = Stakeholder.objects.filter(organization=organization).select_related(
		"related_process",
		"related_document",
		"site",
		"organization",
	)

	search = request.GET.get("search", "").strip()
	stakeholder_type = request.GET.get("stakeholder_type", "")
	process_id = request.GET.get("process_id", "")
	is_active = request.GET.get("is_active", "")

	if search:
		stakeholders = stakeholders.filter(name__icontains=search)
	if stakeholder_type:
		stakeholders = stakeholders.filter(stakeholder_type=stakeholder_type)
	if process_id:
		stakeholders = stakeholders.filter(related_process_id=process_id)
	if is_active in ["true", "false"]:
		stakeholders = stakeholders.filter(is_active=is_active == "true")

	can_edit = can_edit_stakeholders(request.user)
	processes = Process.objects.filter(organization=organization, is_active=True).order_by("code")

	return render(
		request,
		"core/stakeholder_list.html",
		{
			"stakeholders": stakeholders,
			"organization": organization,
			"can_edit": can_edit,
			"stakeholder_types": Stakeholder.StakeholderType.choices,
			"processes": processes,
			"selected_search": search,
			"selected_type": stakeholder_type,
			"selected_process_id": process_id,
			"selected_is_active": is_active,
		},
	)


@login_required
def stakeholder_detail(request, pk):
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	stakeholder = get_object_or_404(
		Stakeholder,
		pk=pk,
		organization=organization,
	)
	can_edit = can_edit_stakeholders(request.user)

	return render(
		request,
		"core/stakeholder_detail.html",
		{
			"stakeholder": stakeholder,
			"organization": organization,
			"can_edit": can_edit,
		},
	)


@login_required
def stakeholder_create(request):
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	if not can_edit_stakeholders(request.user):
		messages.error(request, "No tiene permisos para crear partes interesadas.")
		return redirect("core:stakeholder_list")

	if request.method == "POST":
		form = StakeholderForm(request.POST)
		_configure_stakeholder_form(form, organization)
		if form.is_valid():
			stakeholder = form.save(commit=False)
			stakeholder.organization = organization
			stakeholder.save()
			log_audit_event(
				actor=request.user,
				action="stakeholder_created",
				instance=stakeholder,
				metadata={
					"stakeholder_type": stakeholder.stakeholder_type,
					"related_process_id": stakeholder.related_process_id,
				},
				object_type_override="Stakeholder",
			)
			messages.success(request, "Parte interesada creada correctamente.")
			return redirect("core:stakeholder_detail", pk=stakeholder.pk)
	else:
		form = StakeholderForm()
		_configure_stakeholder_form(form, organization)

	return render(
		request,
		"core/stakeholder_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def stakeholder_edit(request, pk):
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	stakeholder = get_object_or_404(
		Stakeholder,
		pk=pk,
		organization=organization,
	)
	if not can_edit_stakeholders(request.user):
		messages.error(request, "No tiene permisos para editar partes interesadas.")
		return redirect("core:stakeholder_detail", pk=stakeholder.pk)

	if request.method == "POST":
		form = StakeholderForm(request.POST, instance=stakeholder)
		_configure_stakeholder_form(form, organization)
		if form.is_valid():
			stakeholder = form.save(commit=False)
			stakeholder.organization = organization
			stakeholder.save()
			log_audit_event(
				actor=request.user,
				action="stakeholder_updated",
				instance=stakeholder,
				metadata={
					"stakeholder_type": stakeholder.stakeholder_type,
					"related_process_id": stakeholder.related_process_id,
				},
				object_type_override="Stakeholder",
			)
			messages.success(request, "Parte interesada actualizada correctamente.")
			return redirect("core:stakeholder_detail", pk=stakeholder.pk)
	else:
		form = StakeholderForm(instance=stakeholder)
		_configure_stakeholder_form(form, organization)

	return render(
		request,
		"core/stakeholder_form.html",
		{
			"form": form,
			"organization": organization,
			"stakeholder": stakeholder,
			"is_edit": True,
		},
	)
