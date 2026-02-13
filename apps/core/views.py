from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.db.models import Count
from django.shortcuts import redirect, render, get_object_or_404

from apps.core.forms import (
	OrganizationContextForm,
	StakeholderForm,
	RiskOpportunityForm,
	NoConformityForm,
	CAPAActionForm,
)
from apps.core.models import (
	Organization,
	OrganizationContext,
	Site,
	Stakeholder,
	Process,
	RiskOpportunity,
	NoConformity,
	CAPAAction,
)
from apps.core.services import log_audit_event
from apps.core.utils import can_edit_context, can_edit_stakeholders, can_edit_risks, can_edit_nc
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


def _configure_risk_form(form, organization):
	User = get_user_model()
	form.fields["site"].queryset = Site.objects.filter(organization=organization, is_active=True)
	form.fields["related_process"].queryset = Process.objects.filter(
		organization=organization,
		is_active=True,
	).order_by("code")
	form.fields["stakeholder"].queryset = Stakeholder.objects.filter(organization=organization)
	form.fields["owner"].queryset = User.objects.filter(is_active=True)
	form.fields["evidence_document"].queryset = Document.objects.filter(is_active=True)


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


@login_required
def risk_list(request):
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	risks = RiskOpportunity.objects.filter(organization=organization).select_related(
		"related_process",
		"stakeholder",
		"owner",
		"organization",
		"site",
	)

	process_type = request.GET.get("process_type", "")
	process_id = request.GET.get("process_id", "")
	stakeholder_id = request.GET.get("stakeholder_id", "")
	status = request.GET.get("status", "")
	level = request.GET.get("level", "")
	kind = request.GET.get("kind", "")

	if process_type:
		risks = risks.filter(related_process__process_type=process_type)
	if process_id:
		risks = risks.filter(related_process_id=process_id)
	if stakeholder_id:
		risks = risks.filter(stakeholder_id=stakeholder_id)
	if status:
		risks = risks.filter(status=status)
	if level:
		risks = risks.filter(level=level)
	if kind:
		risks = risks.filter(kind=kind)

	can_edit = can_edit_risks(request.user)
	processes = Process.objects.filter(organization=organization, is_active=True).order_by("code")
	stakeholders = Stakeholder.objects.filter(organization=organization).order_by("name")

	return render(
		request,
		"core/risks_list.html",
		{
			"risks": risks,
			"organization": organization,
			"can_edit": can_edit,
			"process_types": Process.ProcessType.choices,
			"processes": processes,
			"stakeholders": stakeholders,
			"status_choices": RiskOpportunity.Status.choices,
			"level_choices": RiskOpportunity.Level.choices,
			"kind_choices": RiskOpportunity.Kind.choices,
			"selected_process_type": process_type,
			"selected_process_id": process_id,
			"selected_stakeholder_id": stakeholder_id,
			"selected_status": status,
			"selected_level": level,
			"selected_kind": kind,
		},
	)


@login_required
def risk_detail(request, pk):
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	risk = get_object_or_404(
		RiskOpportunity,
		pk=pk,
		organization=organization,
	)
	can_edit = can_edit_risks(request.user)

	return render(
		request,
		"core/risks_detail.html",
		{
			"risk": risk,
			"organization": organization,
			"can_edit": can_edit,
		},
	)


@login_required
def risk_create(request):
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	if not can_edit_risks(request.user):
		messages.error(request, "No tiene permisos para crear riesgos u oportunidades.")
		return redirect("core:risk_list")

	if request.method == "POST":
		form = RiskOpportunityForm(request.POST)
		_configure_risk_form(form, organization)
		if form.is_valid():
			risk = form.save(commit=False)
			risk.organization = organization
			risk.save()
			log_audit_event(
				actor=request.user,
				action="risk_created",
				instance=risk,
				metadata={
					"kind": risk.kind,
					"score": risk.score,
					"level": risk.level,
					"process_id": risk.related_process_id,
					"stakeholder_id": risk.stakeholder_id,
					"status": risk.status,
				},
				object_type_override="RiskOpportunity",
			)
			messages.success(request, "Riesgo u oportunidad creado correctamente.")
			return redirect("core:risk_detail", pk=risk.pk)
	else:
		form = RiskOpportunityForm()
		_configure_risk_form(form, organization)

	return render(
		request,
		"core/risks_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def risk_edit(request, pk):
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	risk = get_object_or_404(
		RiskOpportunity,
		pk=pk,
		organization=organization,
	)
	if not can_edit_risks(request.user):
		messages.error(request, "No tiene permisos para editar riesgos u oportunidades.")
		return redirect("core:risk_detail", pk=risk.pk)

	if request.method == "POST":
		form = RiskOpportunityForm(request.POST, instance=risk)
		_configure_risk_form(form, organization)
		if form.is_valid():
			risk = form.save(commit=False)
			risk.organization = organization
			risk.save()
			log_audit_event(
				actor=request.user,
				action="risk_updated",
				instance=risk,
				metadata={
					"kind": risk.kind,
					"score": risk.score,
					"level": risk.level,
					"process_id": risk.related_process_id,
					"stakeholder_id": risk.stakeholder_id,
					"status": risk.status,
				},
				object_type_override="RiskOpportunity",
			)
			messages.success(request, "Riesgo u oportunidad actualizado correctamente.")
			return redirect("core:risk_detail", pk=risk.pk)
	else:
		form = RiskOpportunityForm(instance=risk)
		_configure_risk_form(form, organization)

	return render(
		request,
		"core/risks_form.html",
		{
			"form": form,
			"organization": organization,
			"risk": risk,
			"is_edit": True,
		},
	)


@login_required
def risk_dashboard(request):
	"""
	Dashboard visual de riesgos y oportunidades con matriz 5x5 (Probabilidad vs Impacto).
	Reutiliza los mismos filtros que risk_list.
	"""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	risks = RiskOpportunity.objects.filter(organization=organization)

	# Aplicar los mismos filtros que risk_list
	process_type = request.GET.get("process_type", "")
	process_id = request.GET.get("process_id", "")
	stakeholder_id = request.GET.get("stakeholder_id", "")
	status = request.GET.get("status", "")
	level = request.GET.get("level", "")
	kind = request.GET.get("kind", "")

	if process_type:
		risks = risks.filter(related_process__process_type=process_type)
	if process_id:
		risks = risks.filter(related_process_id=process_id)
	if stakeholder_id:
		risks = risks.filter(stakeholder_id=stakeholder_id)
	if status:
		risks = risks.filter(status=status)
	if level:
		risks = risks.filter(level=level)
	if kind:
		risks = risks.filter(kind=kind)

	# Agregar conteos por probabilidad e impacto (matriz 5x5)
	matrix_data = risks.values("probability", "impact").annotate(count=Count("id"))

	# Construir matriz 5x5 para renderear en template
	# matriz[probabilidad-1][impacto-1] = {count, level_class}
	def get_level_class(probability, impact):
		score = probability * impact
		if score <= 7:
			return "level-low"
		elif score <= 14:
			return "level-medium"
		else:
			return "level-high"

	# Crear dict para acceso rápido
	matrix_dict = {(row["probability"], row["impact"]): row["count"] for row in matrix_data}

	# Construir matriz estructura para el template (filas: prob 5..1, cols: impact 1..5)
	# El riesgo matriz clásica tiene probablidad en Y (de arriba a abajo) e impacto en X
	matrix_grid = []
	for prob in range(5, 0, -1):  # 5, 4, 3, 2, 1
		row = []
		for impact in range(1, 6):  # 1, 2, 3, 4, 5
			count = matrix_dict.get((prob, impact), 0)
			row.append({
				"probability": prob,
				"impact": impact,
				"count": count,
				"level_class": get_level_class(prob, impact),
			})
		matrix_grid.append(row)

	# Contar por nivel (usando los datos filtrados ya que level se calcula desde score)
	level_summary = risks.values("level").annotate(count=Count("id")).order_by("level")
	level_dict = {row["level"]: row["count"] for row in level_summary}

	# Contar por tipo (RISK/OPPORTUNITY)
	kind_summary = risks.values("kind").annotate(count=Count("id")).order_by("kind")
	kind_dict = {row["kind"]: row["count"] for row in kind_summary}

	# Total de riesgos filtrados
	total_risks = risks.count()

	can_edit = can_edit_risks(request.user)
	processes = Process.objects.filter(organization=organization, is_active=True).order_by("code")
	stakeholders = Stakeholder.objects.filter(organization=organization).order_by("name")

	# Armar query string para el botón "Ver Lista"
	query_params = "&".join([
		f"process_type={process_type}" if process_type else "",
		f"process_id={process_id}" if process_id else "",
		f"stakeholder_id={stakeholder_id}" if stakeholder_id else "",
		f"status={status}" if status else "",
		f"level={level}" if level else "",
		f"kind={kind}" if kind else "",
	]).lstrip("&")

	return render(
		request,
		"core/risks_dashboard.html",
		{
			"organization": organization,
			"matrix_grid": matrix_grid,
			"level_summary": level_dict,
			"kind_summary": kind_dict,
			"total_risks": total_risks,
			"can_edit": can_edit,
			"process_types": Process.ProcessType.choices,
			"processes": processes,
			"stakeholders": stakeholders,
			"status_choices": RiskOpportunity.Status.choices,
			"level_choices": RiskOpportunity.Level.choices,
			"kind_choices": RiskOpportunity.Kind.choices,
			"selected_process_type": process_type,
			"selected_process_id": process_id,
			"selected_stakeholder_id": stakeholder_id,
			"selected_status": status,
			"selected_level": level,
			"selected_kind": kind,
			"query_params": query_params,
		},
	)

def _configure_nc_form(form, organization):
	"""Configure NoConformity form with organization-filtered querysets."""
	User = get_user_model()
	form.fields["site"].queryset = Site.objects.filter(organization=organization, is_active=True)
	form.fields["related_process"].queryset = Process.objects.filter(
		organization=organization,
		is_active=True,
	).order_by("code")
	form.fields["related_document"].queryset = Document.objects.filter(is_active=True)
	form.fields["evidence_document"].queryset = Document.objects.filter(is_active=True)
	form.fields["owner"].queryset = User.objects.filter(is_active=True)
	if "detected_by" in form.fields:
		form.fields["detected_by"].queryset = User.objects.filter(is_active=True)
	if "closed_by" in form.fields:
		form.fields["closed_by"].queryset = User.objects.filter(is_active=True)


@login_required
def nc_list(request):
	"""List all no conformities with filters."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	ncs = NoConformity.objects.filter(organization=organization).select_related(
		"related_process",
		"owner",
		"organization",
		"site",
	)

	# Apply filters
	origin = request.GET.get("origin", "")
	severity = request.GET.get("severity", "")
	status = request.GET.get("status", "")
	process_id = request.GET.get("process_id", "")

	if origin:
		ncs = ncs.filter(origin=origin)
	if severity:
		ncs = ncs.filter(severity=severity)
	if status:
		ncs = ncs.filter(status=status)
	if process_id:
		ncs = ncs.filter(related_process_id=process_id)

	can_edit = can_edit_nc(request.user)
	processes = Process.objects.filter(organization=organization, is_active=True).order_by("code")

	return render(
		request,
		"core/nc_list.html",
		{
			"ncs": ncs,
			"organization": organization,
			"can_edit": can_edit,
			"processes": processes,
			"origin_choices": NoConformity.Origin.choices,
			"severity_choices": NoConformity.Severity.choices,
			"status_choices": NoConformity.Status.choices,
			"selected_origin": origin,
			"selected_severity": severity,
			"selected_status": status,
			"selected_process_id": process_id,
		},
	)


@login_required
def nc_detail(request, pk):
	"""Detail view for a no conformity."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	nc = get_object_or_404(
		NoConformity,
		pk=pk,
		organization=organization,
	)
	capa_actions = nc.capa_actions.select_related("owner").order_by("due_date", "created_at")
	capa_done_count = capa_actions.filter(status=CAPAAction.Status.DONE).count()
	capa_total_count = capa_actions.count()
	capa_all_done = capa_total_count > 0 and capa_done_count == capa_total_count
	can_edit = can_edit_nc(request.user)

	return render(
		request,
		"core/nc_detail.html",
		{
			"nc": nc,
			"capa_actions": capa_actions,
			"capa_done_count": capa_done_count,
			"capa_total_count": capa_total_count,
			"capa_all_done": capa_all_done,
			"organization": organization,
			"can_edit": can_edit,
		},
	)


@login_required
def nc_create(request):
	"""Create a new no conformity."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	if not can_edit_nc(request.user):
		messages.error(request, "No tiene permisos para crear no conformidades.")
		return redirect("core:nc_list")

	if request.method == "POST":
		form = NoConformityForm(request.POST)
		_configure_nc_form(form, organization)
		if form.is_valid():
			nc = form.save(commit=False)
			nc.organization = organization
			nc.save()
			log_audit_event(
				actor=request.user,
				action="core.nc.created",
				instance=nc,
				metadata={
					"origin": nc.origin,
					"severity": nc.severity,
					"status": nc.status,
					"process_id": nc.related_process_id,
					"owner_id": nc.owner_id,
				},
				object_type_override="NoConformity",
			)
			messages.success(request, "No conformidad creada correctamente.")
			return redirect("core:nc_detail", pk=nc.pk)
	else:
		form = NoConformityForm()
		_configure_nc_form(form, organization)

	return render(
		request,
		"core/nc_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def nc_edit(request, pk):
	"""Edit an existing no conformity."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	nc = get_object_or_404(
		NoConformity,
		pk=pk,
		organization=organization,
	)
	if not can_edit_nc(request.user):
		messages.error(request, "No tiene permisos para editar no conformidades.")
		return redirect("core:nc_detail", pk=nc.pk)

	if request.method == "POST":
		form = NoConformityForm(request.POST, instance=nc)
		_configure_nc_form(form, organization)
		if form.is_valid():
			nc = form.save(commit=False)
			nc.organization = organization
			nc.save()
			log_audit_event(
				actor=request.user,
				action="core.nc.updated",
				instance=nc,
				metadata={
					"origin": nc.origin,
					"severity": nc.severity,
					"status": nc.status,
					"process_id": nc.related_process_id,
					"owner_id": nc.owner_id,
				},
				object_type_override="NoConformity",
			)
			messages.success(request, "No conformidad actualizada correctamente.")
			return redirect("core:nc_detail", pk=nc.pk)
	else:
		form = NoConformityForm(instance=nc)
		_configure_nc_form(form, organization)

	return render(
		request,
		"core/nc_form.html",
		{
			"form": form,
			"organization": organization,
			"nc": nc,
			"is_edit": True,
		},
	)


# ============================================
# VISTAS CAPA (Acciones de No Conformidades)
# ============================================

def _configure_capa_form(form, organization):
	"""Configurar querysets del formulario CAPA."""
	User = get_user_model()
	form.fields["owner"].queryset = User.objects.filter(is_active=True)
	form.fields["evidence_document"].queryset = Document.objects.filter(is_active=True)


@login_required
def capa_action_create(request, nc_id):
	"""Crear nueva accion CAPA para una NC."""
	# First try to get the NC by ID alone
	nc = get_object_or_404(NoConformity, pk=nc_id)
	organization = nc.organization
	
	# Verify the org is active
	if not organization.is_active:
		messages.error(request, "La organizacion de esta NC no está activa.")
		return redirect("home")

	if not can_edit_nc(request.user):
		messages.error(request, "No tiene permisos para crear acciones CAPA.")
		return redirect("core:nc_detail", pk=nc.pk)

	if request.method == "POST":
		form = CAPAActionForm(request.POST)
		_configure_capa_form(form, organization)
		if form.is_valid():
			capa = form.save(commit=False)
			capa.no_conformity = nc
			capa.organization = organization
			capa.save()
			log_audit_event(
				actor=request.user,
				action="core.capa_action.created",
				instance=capa,
				metadata={
					"nc_id": nc.id,
					"nc_code": nc.code,
					"action_type": capa.action_type,
					"status": capa.status,
					"owner_id": capa.owner_id,
					"due_date": str(capa.due_date) if capa.due_date else None,
				},
				object_type_override="CAPAAction",
			)
			messages.success(request, "Accion CAPA creada correctamente.")
			return redirect("core:nc_detail", pk=nc.pk)
	else:
		form = CAPAActionForm()
		_configure_capa_form(form, organization)

	return render(
		request,
		"core/capa_action_form.html",
		{
			"form": form,
			"nc": nc,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def capa_action_edit(request, action_id):
	"""Editar accion CAPA existente."""
	# Get the CAPA action by ID alone
	capa = get_object_or_404(CAPAAction, pk=action_id)
	organization = capa.organization
	
	# Verify the org is active
	if not organization.is_active:
		messages.error(request, "La organizacion de esta accion CAPA no está activa.")
		return redirect("home")

	if not can_edit_nc(request.user):
		messages.error(request, "No tiene permisos para editar acciones CAPA.")
		return redirect("core:nc_detail", pk=capa.no_conformity.pk)

	if request.method == "POST":
		form = CAPAActionForm(request.POST, instance=capa)
		_configure_capa_form(form, organization)
		if form.is_valid():
			capa = form.save()
			log_audit_event(
				actor=request.user,
				action="core.capa_action.updated",
				instance=capa,
				metadata={
					"nc_id": capa.no_conformity.id,
					"nc_code": capa.no_conformity.code,
					"action_type": capa.action_type,
					"status": capa.status,
					"owner_id": capa.owner_id,
					"due_date": str(capa.due_date) if capa.due_date else None,
				},
				object_type_override="CAPAAction",
			)
			messages.success(request, "Accion CAPA actualizada correctamente.")
			return redirect("core:nc_detail", pk=capa.no_conformity.pk)
	else:
		form = CAPAActionForm(instance=capa)
		_configure_capa_form(form, organization)

	return render(
		request,
		"core/capa_action_form.html",
		{
			"form": form,
			"nc": capa.no_conformity,
			"capa": capa,
			"organization": organization,
			"is_edit": True,
		},
	)