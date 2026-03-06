from datetime import date, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import redirect, render, get_object_or_404

from apps.core.forms import (
	OrganizationContextForm,
	StakeholderForm,
	RiskOpportunityForm,
	NoConformityForm,
	CAPAActionForm,
	QualityObjectiveForm,
	InternalAuditForm,
	AuditAnswerFormSet,
	AuditFindingForm,
	AuditQuestionForm,
	ManagementReviewForm,
	QualityIndicatorForm,
	IndicatorMeasurementForm,
	NonconformingOutputForm,
	SupplierForm,
	SupplierEvaluationForm,
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
	QualityObjective,
	InternalAudit,
	AuditQuestion,
	AuditAnswer,
	AuditFinding,
	ManagementReview,
	QualityIndicator,
	IndicatorMeasurement,
	NonconformingOutput,
	Supplier,
	SupplierEvaluation,
)
from apps.core.services import log_audit_event
from apps.core.utils import (
	can_edit_context,
	can_edit_stakeholders,
	can_edit_risks,
	can_edit_nc,
	can_edit_objective,
	can_edit_audit,
	can_edit_nonconforming_output,
	can_edit_supplier,
)
from apps.docs.models import Document


@login_required
def home(request):
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	
	# Get findings statistics
	findings_stats = {
		"total": 0,
		"nonconformity": 0,
		"area_of_concern": 0,
		"improvement_opportunity": 0,
		"recent": []
	}
	
	if organization:
		findings = AuditFinding.objects.filter(audit__organization=organization).select_related("audit", "related_process")
		findings_stats["total"] = findings.count()
		findings_stats["nonconformity"] = findings.filter(finding_type=AuditFinding.FindingType.NONCONFORMITY).count()
		findings_stats["area_of_concern"] = findings.filter(finding_type=AuditFinding.FindingType.AREA_OF_CONCERN).count()
		findings_stats["improvement_opportunity"] = findings.filter(finding_type=AuditFinding.FindingType.IMPROVEMENT_OPPORTUNITY).count()
		findings_stats["recent"] = findings.order_by("-created_at")[:5]
	
	return render(request, "home.html", {
		"organization": organization,
		"findings_stats": findings_stats,
	})


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
	is_htmx = request.headers.get("HX-Request") == "true"

	context = {
		"stakeholders": stakeholders,
		"organization": organization,
		"can_edit": can_edit,
		"stakeholder_types": Stakeholder.StakeholderType.choices,
		"processes": processes,
		"selected_search": search,
		"selected_type": stakeholder_type,
		"selected_process_id": process_id,
		"selected_is_active": is_active,
	}

	if is_htmx:
		return render(request, "core/stakeholders/_list_results.html", context)

	return render(
		request,
		"core/stakeholder_list.html",
		context,
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
	is_htmx = request.headers.get("HX-Request") == "true"

	context = {
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
	}

	if is_htmx:
		return render(request, "core/risks/_list_results.html", context)

	return render(
		request,
		"core/risks_list.html",
		context,
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

	context = {
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
	}

	if request.headers.get("HX-Request") == "true":
		return render(request, "core/risks/_dashboard_results.html", context)

	return render(
		request,
		"core/risks_dashboard.html",
		context,
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
	is_htmx = request.headers.get("HX-Request") == "true"

	context = {
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
	}

	if is_htmx:
		return render(request, "core/nc/_list_results.html", context)

	return render(
		request,
		"core/nc_list.html",
		context,
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
			# Auto-set closed_by cuando se cierra la NC
			if nc.status == NoConformity.Status.CLOSED and not nc.closed_by:
				nc.closed_by = request.user
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
			try:
				# Manually run model validation since _post_clean() is overridden
				capa.clean()
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
			except ValidationError as e:
				# Add model validation errors fromclean() to form
				if hasattr(e, 'error_dict'):
					for field, error_list in e.error_dict.items():
						for error in error_list:
							form.add_error(field, error.message if hasattr(error, 'message') else str(error))
				else:
					form.add_error(None, str(e))
				# Re-render form with errors
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
		else:
			# Handle form field validation errors
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
def capa_action_create_from_finding(request, pk):
	"""Crear nueva accion CAPA desde un hallazgo (no NONCONFORMITY)."""
	finding = get_object_or_404(AuditFinding, pk=pk)
	organization = finding.audit.organization
	
	# Verify the org is active
	if not organization.is_active:
		messages.error(request, "La organizacion de esta auditoria no está activa.")
		return redirect("home")

	# Reject NONCONFORMITY findings (they should use the NC flow)
	if finding.finding_type == AuditFinding.FindingType.NONCONFORMITY:
		messages.error(request, "Los hallazgos de tipo No conformidad deben usar el flujo de No conformidades.")
		return redirect("core:audit_detail", pk=finding.audit.pk)

	if not can_edit_nc(request.user):
		messages.error(request, "No tiene permisos para crear acciones CAPA.")
		return redirect("core:audit_detail", pk=finding.audit.pk)

	if request.method == "POST":
		form = CAPAActionForm(request.POST)
		_configure_capa_form(form, organization)
		if form.is_valid():
			capa = form.save(commit=False)
			capa.finding = finding
			capa.organization = organization
			try:
				# Manually run model validation since _post_clean() is overridden
				capa.clean()
				capa.save()
				log_audit_event(
					actor=request.user,
					action="core.capa_action.created_from_finding",
					instance=capa,
					metadata={
						"finding_id": finding.id,
						"audit_id": finding.audit.id,
						"finding_type": finding.finding_type,
						"action_type": capa.action_type,
						"status": capa.status,
						"owner_id": capa.owner_id,
						"due_date": str(capa.due_date) if capa.due_date else None,
					},
					object_type_override="CAPAAction",
				)
				messages.success(request, "Accion CAPA creada correctamente desde el hallazgo.")
				return redirect("core:audit_detail", pk=finding.audit.pk)
			except ValidationError as e:
				# Add model validation errors from clean() to form
				if hasattr(e, 'error_dict'):
					for field, error_list in e.error_dict.items():
						for error in error_list:
							form.add_error(field, error.message if hasattr(error, 'message') else str(error))
				else:
					form.add_error(None, str(e))
				# Re-render form with errors
				return render(
					request,
					"core/capa_action_form.html",
					{
						"form": form,
						"finding": finding,
						"organization": organization,
						"is_edit": False,
					},
				)
		else:
			# Handle form field validation errors
			return render(
				request,
				"core/capa_action_form.html",
				{
					"form": form,
					"finding": finding,
					"organization": organization,
					"is_edit": False,
				},
			)
	else:
		form = CAPAActionForm()
		_configure_capa_form(form, organization)

	return render(
		request,
		"core/capa_action_form.html",
		{
			"form": form,
			"finding": finding,
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
			try:
				capa.full_clean()  # Run model validation before save
				capa = form.save()
				log_audit_event(
					actor=request.user,
					action="core.capa_action.updated",
					instance=capa,
					metadata={
						"nc_id": capa.no_conformity.id if capa.no_conformity else None,
						"nc_code": capa.no_conformity.code if capa.no_conformity else None,
						"finding_id": capa.finding.id if capa.finding else None,
						"action_type": capa.action_type,
						"status": capa.status,
						"owner_id": capa.owner_id,
						"due_date": str(capa.due_date) if capa.due_date else None,
						"effectiveness_result": capa.effectiveness_result or None,
						"effectiveness_date": str(capa.effectiveness_date) if capa.effectiveness_date else None,
						"effectiveness_notes": capa.effectiveness_notes or None,
					},
					object_type_override="CAPAAction",
				)
				messages.success(request, "Accion CAPA actualizada correctamente.")
				if capa.no_conformity:
					return redirect("core:nc_detail", pk=capa.no_conformity.pk)
				elif capa.finding:
					return redirect("core:audit_detail", pk=capa.finding.audit.pk)
			except ValidationError as e:
				# Add model validation errors to form
				for field, error_list in e.error_dict.items():
					for error in error_list:
						form.add_error(field, error.message)
				# Re-render form with errors
				return render(
					request,
					"core/capa_action_form.html",
					{
						"form": form,
						"nc": capa.no_conformity,
						"finding": capa.finding,
						"capa": capa,
						"organization": organization,
						"is_edit": True,
					},
				)
		else:
			# Handle form validation errors
			return render(
				request,
				"core/capa_action_form.html",
				{
					"form": form,
					"nc": capa.no_conformity,
					"finding": capa.finding,
					"capa": capa,
					"organization": organization,
					"is_edit": True,
				},
			)


def _configure_objective_form(form, organization):
	"""Configura los QuerySets de campos relacionales en el formulario de objetivos."""
	User = get_user_model()
	form.fields["site"].queryset = Site.objects.filter(
		organization=organization,
		is_active=True,
	)
	form.fields["related_process"].queryset = Process.objects.filter(
		organization=organization,
		is_active=True,
	).order_by("code")
	form.fields["owner"].queryset = User.objects.filter(is_active=True)


@login_required
def quality_objective_list(request):
	"""Lista de objetivos de calidad con filtros."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	objectives = QualityObjective.objects.filter(
		organization=organization,
	).select_related(
		"related_process",
		"owner",
		"site",
		"organization",
	)

	# Filtros
	status = request.GET.get("status", "")
	process_id = request.GET.get("process_id", "")
	owner_id = request.GET.get("owner_id", "")

	if status:
		objectives = objectives.filter(status=status)
	if process_id:
		objectives = objectives.filter(related_process_id=process_id)
	if owner_id:
		objectives = objectives.filter(owner_id=owner_id)

	# Calcular porcentajes para cada objetivo
	objectives_with_progress = []
	for obj in objectives:
		if obj.target_value > 0:
			progress = min((obj.current_value / obj.target_value) * 100, 100)
		else:
			progress = 0
		objectives_with_progress.append({
			'obj': obj,
			'progress': progress
		})

	can_edit = can_edit_objective(request.user)
	User = get_user_model()
	processes = Process.objects.filter(
		organization=organization,
		is_active=True,
	).order_by("code")
	owners = User.objects.filter(is_active=True).filter(
		quality_objectives__organization=organization,
	).distinct()
	is_htmx = request.headers.get("HX-Request") == "true"

	context = {
		"objectives": objectives_with_progress,
		"organization": organization,
		"can_edit": can_edit,
		"status_choices": QualityObjective.Status.choices,
		"processes": processes,
		"owners": owners,
		"selected_status": status,
		"selected_process_id": process_id,
		"selected_owner_id": owner_id,
	}

	if is_htmx:
		return render(request, "core/objectives/_list_results.html", context)

	return render(
		request,
		"core/objective_list.html",
		context,
	)


@login_required
def quality_objective_detail(request, pk):
	"""Detalle de un objetivo de calidad."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	objective = get_object_or_404(
		QualityObjective,
		pk=pk,
		organization=organization,
	)
	can_edit = can_edit_objective(request.user)

	# Calcular porcentaje
	if objective.target_value > 0:
		progress_percent = (objective.current_value / objective.target_value) * 100
		progress_percent = min(progress_percent, 100)  # No exceder 100%
	else:
		progress_percent = 0

	return render(
		request,
		"core/objective_detail.html",
		{
			"objective": objective,
			"organization": organization,
			"can_edit": can_edit,
			"progress_percent": progress_percent,
		},
	)


@login_required
def quality_objective_create(request):
	"""Crear un nuevo objetivo de calidad."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	if not can_edit_objective(request.user):
		messages.error(request, "No tiene permisos para crear objetivos de calidad.")
		return redirect("core:quality_objective_list")

	if request.method == "POST":
		form = QualityObjectiveForm(request.POST)
		_configure_objective_form(form, organization)
		if form.is_valid():
			objective = form.save(commit=False)
			objective.organization = organization
			objective.save()
			log_audit_event(
				actor=request.user,
				action="core.objective.created",
				instance=objective,
				metadata={
					"title": objective.title,
					"indicator": objective.indicator,
					"target_value": objective.target_value,
					"status": objective.status,
				},
				object_type_override="QualityObjective",
			)
			messages.success(request, "Objetivo de calidad creado correctamente.")
			return redirect("core:quality_objective_detail", pk=objective.pk)
	else:
		form = QualityObjectiveForm()
		_configure_objective_form(form, organization)

	return render(
		request,
		"core/objective_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def quality_objective_edit(request, pk):
	"""Editar un objetivo de calidad."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	objective = get_object_or_404(
		QualityObjective,
		pk=pk,
		organization=organization,
	)

	if not can_edit_objective(request.user):
		messages.error(request, "No tiene permisos para editar objetivos de calidad.")
		return redirect("core:quality_objective_detail", pk=objective.pk)

	if request.method == "POST":
		form = QualityObjectiveForm(request.POST, instance=objective)
		_configure_objective_form(form, organization)
		if form.is_valid():
			objective = form.save(commit=False)
			objective.organization = organization
			objective.save()
			log_audit_event(
				actor=request.user,
				action="core.objective.updated",
				instance=objective,
				metadata={
					"title": objective.title,
					"indicator": objective.indicator,
					"current_value": objective.current_value,
					"status": objective.status,
				},
				object_type_override="QualityObjective",
			)
			messages.success(request, "Objetivo de calidad actualizado correctamente.")
			return redirect("core:quality_objective_detail", pk=objective.pk)
	else:
		form = QualityObjectiveForm(instance=objective)
		_configure_objective_form(form, organization)

	return render(
		request,
		"core/objective_form.html",
		{
			"form": form,
			"objective": objective,
			"organization": organization,
			"is_edit": True,
		},
	)


# ============================================
# AUDITORIAS (ISO 9001 9.2)
# ============================================

def _configure_audit_form(form, organization):
	"""Configurar querysets del formulario de auditorias."""
	User = get_user_model()
	form.fields["site"].queryset = Site.objects.filter(organization=organization, is_active=True)
	form.fields["auditor"].queryset = User.objects.filter(is_active=True)
	form.fields["related_processes"].queryset = Process.objects.filter(
		organization=organization,
		is_active=True,
	).order_by("code")
	form.fields["evidence_document"].queryset = Document.objects.filter(is_active=True)


def _configure_finding_form(form, organization):
	form.fields["related_process"].queryset = Process.objects.filter(
		organization=organization,
		is_active=True,
	).order_by("code")


def _get_audit_questions(audit):
	process_types = list(
		audit.related_processes.values_list("process_type", flat=True).distinct()
	)
	questions = AuditQuestion.objects.filter(
		organization=audit.organization,
		is_active=True,
	)
	if process_types:
		questions = questions.filter(
			Q(process_type__isnull=True) | Q(process_type__in=process_types)
		)
	else:
		questions = questions.filter(process_type__isnull=True)
	return questions.order_by("ordering", "id")


@login_required
def audit_question_list(request):
	"""Listado de preguntas de auditoria."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para gestionar preguntas de auditoria.")
		return redirect("home")

	questions = AuditQuestion.objects.filter(organization=organization)

	is_active = request.GET.get("is_active", "")
	process_type = request.GET.get("process_type", "")
	search = request.GET.get("search", "").strip()

	if is_active in ["true", "false"]:
		questions = questions.filter(is_active=is_active == "true")
	if process_type:
		questions = questions.filter(process_type=process_type)
	if search:
		questions = questions.filter(text__icontains=search)

	questions = questions.order_by("ordering", "id")
	is_htmx = request.headers.get("HX-Request") == "true"

	context = {
		"questions": questions,
		"organization": organization,
		"process_types": Process.ProcessType.choices,
		"selected_is_active": is_active,
		"selected_process_type": process_type,
		"selected_search": search,
	}

	if is_htmx:
		return render(request, "core/audit_questions/_list_results.html", context)

	return render(
		request,
		"core/audit_question_list.html",
		context,
	)


@login_required
def audit_question_create(request):
	"""Crear una pregunta de auditoria."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para crear preguntas de auditoria.")
		return redirect("core:audit_question_list")

	if request.method == "POST":
		form = AuditQuestionForm(request.POST)
		if form.is_valid():
			question = form.save(commit=False)
			question.organization = organization
			question.save()
			log_audit_event(
				actor=request.user,
				action="core.audit_question.created",
				instance=question,
				metadata={
					"process_type": question.process_type,
					"is_active": question.is_active,
					"ordering": question.ordering,
				},
				object_type_override="AuditQuestion",
			)
			messages.success(request, "Pregunta creada correctamente.")
			return redirect("core:audit_question_list")
	else:
		form = AuditQuestionForm()

	return render(
		request,
		"core/audit_question_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def audit_question_edit(request, pk):
	"""Editar una pregunta de auditoria."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	question = get_object_or_404(
		AuditQuestion,
		pk=pk,
		organization=organization,
	)

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para editar preguntas de auditoria.")
		return redirect("core:audit_question_list")

	if request.method == "POST":
		form = AuditQuestionForm(request.POST, instance=question)
		if form.is_valid():
			question = form.save()
			log_audit_event(
				actor=request.user,
				action="core.audit_question.updated",
				instance=question,
				metadata={
					"process_type": question.process_type,
					"is_active": question.is_active,
					"ordering": question.ordering,
				},
				object_type_override="AuditQuestion",
			)
			messages.success(request, "Pregunta actualizada correctamente.")
			return redirect("core:audit_question_list")
	else:
		form = AuditQuestionForm(instance=question)

	return render(
		request,
		"core/audit_question_form.html",
		{
			"form": form,
			"organization": organization,
			"question": question,
			"is_edit": True,
		},
	)


@login_required
def audit_question_toggle(request, pk):
	"""Activar o desactivar una pregunta de auditoria."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	question = get_object_or_404(
		AuditQuestion,
		pk=pk,
		organization=organization,
	)

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para actualizar preguntas de auditoria.")
		return redirect("core:audit_question_list")

	if request.method != "POST":
		messages.error(request, "Accion invalida.")
		return redirect("core:audit_question_list")

	question.is_active = not question.is_active
	question.save(update_fields=["is_active"])
	log_audit_event(
		actor=request.user,
		action="core.audit_question.toggled",
		instance=question,
		metadata={
			"process_type": question.process_type,
			"is_active": question.is_active,
			"ordering": question.ordering,
		},
		object_type_override="AuditQuestion",
	)

	messages.success(request, "Pregunta actualizada correctamente.")
	return redirect("core:audit_question_list")


@login_required
def audit_list(request):
	"""Lista de auditorias internas con filtros."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	audits = InternalAudit.objects.filter(organization=organization).select_related(
		"site",
		"auditor",
		"evidence_document",
		"organization",
	).prefetch_related("related_processes")

	status = request.GET.get("status", "")
	process_id = request.GET.get("process_id", "")
	date_from = request.GET.get("date_from", "")
	date_to = request.GET.get("date_to", "")

	if status:
		audits = audits.filter(status=status)
	if process_id:
		audits = audits.filter(related_processes__id=process_id)
	if date_from:
		audits = audits.filter(audit_date__gte=date_from)
	if date_to:
		audits = audits.filter(audit_date__lte=date_to)

	audits = audits.distinct().order_by("-audit_date", "title")

	can_edit = can_edit_audit(request.user)
	processes = Process.objects.filter(organization=organization, is_active=True).order_by("code")
	is_htmx = request.headers.get("HX-Request") == "true"

	context = {
		"audits": audits,
		"organization": organization,
		"can_edit": can_edit,
		"status_choices": InternalAudit.Status.choices,
		"processes": processes,
		"selected_status": status,
		"selected_process_id": process_id,
		"selected_date_from": date_from,
		"selected_date_to": date_to,
	}

	if is_htmx:
		return render(request, "core/audits/_list_results.html", context)

	return render(
		request,
		"core/audit_list.html",
		context,
	)


@login_required
def audit_detail(request, pk):
	"""Detalle de auditoria interna."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	audit = get_object_or_404(
		InternalAudit,
		pk=pk,
		organization=organization,
	)

	answers = audit.answers.select_related("question")
	counts = {
		"OK": answers.filter(result=AuditAnswer.Result.OK).count(),
		"NOT_OK": answers.filter(result=AuditAnswer.Result.NOT_OK).count(),
		"NA": answers.filter(result=AuditAnswer.Result.NA).count(),
	}
	findings = audit.findings.select_related("related_process", "nc")
	can_edit = can_edit_audit(request.user)

	return render(
		request,
		"core/audit_detail.html",
		{
			"audit": audit,
			"organization": organization,
			"can_edit": can_edit,
			"answer_counts": counts,
			"findings": findings,
		},
	)


@login_required
def audit_create(request):
	"""Crear una nueva auditoria interna."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para crear auditorias internas.")
		return redirect("core:audit_list")

	if request.method == "POST":
		form = InternalAuditForm(request.POST, request.FILES)
		_configure_audit_form(form, organization)
		if form.is_valid():
			audit = form.save(commit=False)
			audit.organization = organization
			audit.save()
			form.save_m2m()
			log_audit_event(
				actor=request.user,
				action="core.audit.created",
				instance=audit,
				metadata={
					"title": audit.title,
					"status": audit.status,
					"audit_date": str(audit.audit_date),
					"audit_type": audit.audit_type,
					"plan_file": bool(audit.plan_file),
					"report_file": bool(audit.report_file),
					"team_cv_file": bool(audit.team_cv_file),
				},
				object_type_override="InternalAudit",
			)
			messages.success(request, "Auditoria interna creada correctamente.")
			return redirect("core:audit_detail", pk=audit.pk)
	else:
		form = InternalAuditForm()
		_configure_audit_form(form, organization)

	return render(
		request,
		"core/audit_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def audit_edit(request, pk):
	"""Editar auditoria interna."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	audit = get_object_or_404(
		InternalAudit,
		pk=pk,
		organization=organization,
	)

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para editar auditorias internas.")
		return redirect("core:audit_detail", pk=audit.pk)

	if request.method == "POST":
		form = InternalAuditForm(request.POST, request.FILES, instance=audit)
		_configure_audit_form(form, organization)
		if form.is_valid():
			audit = form.save(commit=False)
			audit.organization = organization
			audit.save()
			form.save_m2m()
			log_audit_event(
				actor=request.user,
				action="core.audit.updated",
				instance=audit,
				metadata={
					"title": audit.title,
					"status": audit.status,
					"audit_date": str(audit.audit_date),
					"audit_type": audit.audit_type,
					"plan_file": bool(audit.plan_file),
					"report_file": bool(audit.report_file),
					"team_cv_file": bool(audit.team_cv_file),
				},
				object_type_override="InternalAudit",
			)
			messages.success(request, "Auditoria interna actualizada correctamente.")
			return redirect("core:audit_detail", pk=audit.pk)
	else:
		form = InternalAuditForm(instance=audit)
		_configure_audit_form(form, organization)

	return render(
		request,
		"core/audit_form.html",
		{
			"form": form,
			"organization": organization,
			"audit": audit,
			"is_edit": True,
		},
	)


@login_required
def audit_checklist(request, pk):
	"""Responder checklist de auditoria."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	audit = get_object_or_404(
		InternalAudit,
		pk=pk,
		organization=organization,
	)

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para auditar.")
		return redirect("core:audit_detail", pk=audit.pk)

	questions = _get_audit_questions(audit)
	for question in questions:
		AuditAnswer.objects.get_or_create(
			audit=audit,
			question=question,
			defaults={"result": AuditAnswer.Result.NA},
		)

	answers = audit.answers.select_related("question").order_by("question__ordering", "id")

	if request.method == "POST":
		formset = AuditAnswerFormSet(request.POST, instance=audit, queryset=answers, prefix="answers")
		for form in formset.forms:
			form.fields["question"].widget = forms.HiddenInput()
		if formset.is_valid():
			formset.save()
			log_audit_event(
				actor=request.user,
				action="core.audit.checklist.submitted",
				instance=audit,
				metadata={
					"ok": answers.filter(result=AuditAnswer.Result.OK).count(),
					"not_ok": answers.filter(result=AuditAnswer.Result.NOT_OK).count(),
					"na": answers.filter(result=AuditAnswer.Result.NA).count(),
				},
				object_type_override="InternalAudit",
			)
			messages.success(request, "Checklist actualizado correctamente.")
			return redirect("core:audit_detail", pk=audit.pk)
	else:
		formset = AuditAnswerFormSet(instance=audit, queryset=answers, prefix="answers")
		for form in formset.forms:
			form.fields["question"].widget = forms.HiddenInput()

	return render(
		request,
		"core/audit_checklist.html",
		{
			"audit": audit,
			"organization": organization,
			"formset": formset,
			"questions": questions,
		},
	)


@login_required
def audit_finding_create(request, pk):
	"""Crear hallazgo de auditoria."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	audit = get_object_or_404(
		InternalAudit,
		pk=pk,
		organization=organization,
	)

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para registrar hallazgos.")
		return redirect("core:audit_detail", pk=audit.pk)

	if request.method == "POST":
		form = AuditFindingForm(request.POST)
		_configure_finding_form(form, organization)
		if form.is_valid():
			finding = form.save(commit=False)
			finding.audit = audit
			finding.save()
			log_audit_event(
				actor=request.user,
				action="core.audit.finding.created",
				instance=finding,
				metadata={
					"audit_id": audit.id,
					"finding_type": finding.finding_type,
				},
				object_type_override="AuditFinding",
			)
			messages.success(request, "Hallazgo creado correctamente.")
			return redirect("core:audit_detail", pk=audit.pk)
	else:
		form = AuditFindingForm()
		_configure_finding_form(form, organization)

	return render(
		request,
		"core/audit_finding_form.html",
		{
			"form": form,
			"audit": audit,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def audit_finding_edit(request, pk):
	"""Editar hallazgo de auditoria."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	finding = get_object_or_404(
		AuditFinding,
		pk=pk,
	)
	if finding.audit.organization_id != organization.id:
		messages.error(request, "No tiene acceso a este hallazgo.")
		return redirect("core:audit_list")

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para editar hallazgos.")
		return redirect("core:audit_detail", pk=finding.audit.pk)

	if request.method == "POST":
		form = AuditFindingForm(request.POST, instance=finding)
		_configure_finding_form(form, organization)
		if form.is_valid():
			finding = form.save()
			log_audit_event(
				actor=request.user,
				action="core.audit.finding.updated",
				instance=finding,
				metadata={
					"audit_id": finding.audit_id,
					"finding_type": finding.finding_type,
				},
				object_type_override="AuditFinding",
			)
			messages.success(request, "Hallazgo actualizado correctamente.")
			return redirect("core:audit_detail", pk=finding.audit.pk)
	else:
		form = AuditFindingForm(instance=finding)
		_configure_finding_form(form, organization)

	return render(
		request,
		"core/audit_finding_form.html",
		{
			"form": form,
			"audit": finding.audit,
			"organization": organization,
			"finding": finding,
			"is_edit": True,
		},
	)


@login_required
def audit_finding_create_nc(request, pk):
	"""Crear NC desde un hallazgo de auditoria."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	finding = get_object_or_404(
		AuditFinding,
		pk=pk,
	)
	if finding.audit.organization_id != organization.id:
		messages.error(request, "No tiene acceso a este hallazgo.")
		return redirect("core:audit_list")

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para crear NC desde hallazgos.")
		return redirect("core:audit_detail", pk=finding.audit.pk)

	if finding.finding_type != AuditFinding.FindingType.NONCONFORMITY:
		messages.error(request, "Solo puede crear NC desde hallazgos de tipo no conformidad.")
		return redirect("core:audit_detail", pk=finding.audit.pk)

	if finding.nc_id:
		messages.info(request, "Este hallazgo ya tiene una NC asociada.")
		return redirect("core:audit_detail", pk=finding.audit.pk)

	from django.utils import timezone

	# Determine origin based on audit type
	audit_origin = (
		NoConformity.Origin.EXTERNAL_AUDIT
		if finding.audit.audit_type == InternalAudit.AuditType.EXTERNAL
		else NoConformity.Origin.INTERNAL_AUDIT
	)

	nc = NoConformity.objects.create(
		organization=finding.audit.organization,
		site=finding.audit.site,
		related_process=finding.related_process,
		title=f"Hallazgo auditoria: {finding.audit.title}",
		description=finding.description,
		origin=audit_origin,
		severity=finding.severity or NoConformity.Severity.MINOR,
		detected_at=timezone.now().date(),
		detected_by=request.user,
		owner=finding.audit.auditor,
		status=NoConformity.Status.OPEN,
	)

	finding.nc = nc
	finding.save(update_fields=["nc"])

	log_audit_event(
		actor=request.user,
		action="core.audit.finding.nc_created",
		instance=finding,
		metadata={
			"audit_id": finding.audit_id,
			"nc_id": nc.id,
			"nc_code": nc.code,
		},
		object_type_override="AuditFinding",
	)

	messages.success(request, "NC creada correctamente desde el hallazgo.")
	return redirect("core:nc_detail", pk=nc.pk)


# ==========================================
# Management Review Views
# ==========================================


@login_required
def review_list(request):
	"""Lista de revisiones por la direccion."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	reviews = ManagementReview.objects.filter(
		organization=organization
	).select_related("chairperson", "organization").order_by("-review_date")

	can_edit = can_edit_audit(request.user)

	return render(
		request,
		"core/review_list.html",
		{
			"reviews": reviews,
			"organization": organization,
			"can_edit": can_edit,
		},
	)


@login_required
def review_detail(request, pk):
	"""Detalle de revision por la direccion."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	review = get_object_or_404(
		ManagementReview,
		pk=pk,
		organization=organization,
	)

	can_edit = can_edit_audit(request.user)

	return render(
		request,
		"core/review_detail.html",
		{
			"review": review,
			"organization": organization,
			"can_edit": can_edit,
		},
	)


@login_required
def review_create(request):
	"""Crear nueva revision por la direccion."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para crear revisiones por la direccion.")
		return redirect("core:review_list")

	if request.method == "POST":
		form = ManagementReviewForm(request.POST, request.FILES)
		if form.is_valid():
			review = form.save(commit=False)
			review.organization = organization
			review.save()
			log_audit_event(
				actor=request.user,
				action="core.management_review.created",
				instance=review,
				metadata={
					"review_date": str(review.review_date),
				},
				object_type_override="ManagementReview",
			)
			messages.success(request, "Revision por la direccion creada correctamente.")
			return redirect("core:review_detail", pk=review.pk)
	else:
		form = ManagementReviewForm()

	return render(
		request,
		"core/review_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def review_edit(request, pk):
	"""Editar revision por la direccion."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	review = get_object_or_404(
		ManagementReview,
		pk=pk,
		organization=organization,
	)

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para editar revisiones por la direccion.")
		return redirect("core:review_detail", pk=review.pk)

	if request.method == "POST":
		form = ManagementReviewForm(request.POST, request.FILES, instance=review)
		if form.is_valid():
			review = form.save()
			log_audit_event(
				actor=request.user,
				action="core.management_review.updated",
				instance=review,
				metadata={
					"review_date": str(review.review_date),
				},
				object_type_override="ManagementReview",
			)
			messages.success(request, "Revision por la direccion actualizada correctamente.")
			return redirect("core:review_detail", pk=review.pk)
	else:
		form = ManagementReviewForm(instance=review)

	return render(
		request,
		"core/review_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": True,
			"review": review,
		},
	)


# ==========================================
# Quality Indicator Views
# ==========================================


@login_required
def indicator_list(request):
	"""Lista de indicadores de calidad."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	indicators = QualityIndicator.objects.filter(
		organization=organization,
		is_active=True
	).select_related("related_process", "organization").prefetch_related("measurements")

	process_id = request.GET.get("process_id", "")
	if process_id:
		indicators = indicators.filter(related_process_id=process_id)

	can_edit = can_edit_audit(request.user)
	processes = Process.objects.filter(organization=organization, is_active=True).order_by("code")
	is_htmx = request.headers.get("HX-Request") == "true"

	context = {
		"indicators": indicators,
		"organization": organization,
		"can_edit": can_edit,
		"processes": processes,
		"selected_process_id": process_id,
	}

	if is_htmx:
		return render(request, "core/indicators/_list_results.html", context)

	return render(
		request,
		"core/indicator_list.html",
		context,
	)


@login_required
def indicator_detail(request, pk):
	"""Detalle de indicador de calidad."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	indicator = get_object_or_404(
		QualityIndicator,
		pk=pk,
		organization=organization,
	)

	measurements = indicator.measurements.all()[:12]
	can_edit = can_edit_audit(request.user)

	return render(
		request,
		"core/indicator_detail.html",
		{
			"indicator": indicator,
			"measurements": measurements,
			"organization": organization,
			"can_edit": can_edit,
		},
	)


@login_required
def indicator_create(request):
	"""Crear nuevo indicador de calidad."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para crear indicadores.")
		return redirect("core:indicator_list")

	if request.method == "POST":
		form = QualityIndicatorForm(request.POST)
		if form.is_valid():
			indicator = form.save(commit=False)
			indicator.organization = organization
			indicator.save()
			log_audit_event(
				actor=request.user,
				action="core.indicator.created",
				instance=indicator,
				metadata={
					"indicator_id": indicator.id,
					"name": indicator.name,
					"target_value": str(indicator.target_value),
				},
				object_type_override="QualityIndicator",
			)
			messages.success(request, "Indicador de calidad creado correctamente.")
			return redirect("core:indicator_detail", pk=indicator.pk)
	else:
		form = QualityIndicatorForm()

	return render(
		request,
		"core/indicator_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": False,
		},
	)


@login_required
def indicator_edit(request, pk):
	"""Editar indicador de calidad."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	indicator = get_object_or_404(
		QualityIndicator,
		pk=pk,
		organization=organization,
	)

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para editar indicadores.")
		return redirect("core:indicator_detail", pk=indicator.pk)

	if request.method == "POST":
		form = QualityIndicatorForm(request.POST, instance=indicator)
		if form.is_valid():
			indicator = form.save()
			log_audit_event(
				actor=request.user,
				action="core.indicator.updated",
				instance=indicator,
				metadata={
					"indicator_id": indicator.id,
					"name": indicator.name,
					"target_value": str(indicator.target_value),
				},
				object_type_override="QualityIndicator",
			)
			messages.success(request, "Indicador de calidad actualizado correctamente.")
			return redirect("core:indicator_detail", pk=indicator.pk)
	else:
		form = QualityIndicatorForm(instance=indicator)

	return render(
		request,
		"core/indicator_form.html",
		{
			"form": form,
			"organization": organization,
			"is_edit": True,
			"indicator": indicator,
		},
	)


@login_required
def measurement_create(request, indicator_pk):
	"""Crear nueva medición de indicador."""
	organization = _get_current_organization()
	if organization is None:
		messages.error(request, "No hay organizacion activa.")
		return redirect("home")

	indicator = get_object_or_404(
		QualityIndicator,
		pk=indicator_pk,
		organization=organization,
	)

	if not can_edit_audit(request.user):
		messages.error(request, "No tiene permisos para registrar mediciones.")
		return redirect("core:indicator_detail", pk=indicator.pk)

	if request.method == "POST":
		form = IndicatorMeasurementForm(request.POST)
		if form.is_valid():
			measurement = form.save(commit=False)
			measurement.indicator = indicator
			measurement.save()
			log_audit_event(
				actor=request.user,
				action="core.indicator.measurement.created",
				instance=measurement,
				metadata={
					"indicator_id": indicator.id,
					"value": str(measurement.value),
					"measurement_date": str(measurement.measurement_date),
				},
				object_type_override="IndicatorMeasurement",
			)
			messages.success(request, "Medición registrada correctamente.")
			return redirect("core:indicator_detail", pk=indicator.pk)
	else:
		form = IndicatorMeasurementForm()

	return render(
		request,
		"core/measurement_form.html",
		{
			"form": form,
			"indicator": indicator,
			"organization": organization,
		},
	)


# ===== NonconformingOutput (ISO 8.7) Views =====

@login_required
def nonconforming_output_list(request):
	"""Lista de Productos/Servicios No Conformes."""
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	outputs = NonconformingOutput.objects.filter(
		organization=organization,
		is_active=True,
	).select_related("site", "related_process", "detected_by", "responsible", "linked_nc")

	# Filtros
	status = request.GET.get("status")
	if status:
		outputs = outputs.filter(status=status)

	severity = request.GET.get("severity")
	if severity:
		outputs = outputs.filter(severity=severity)

	disposition = request.GET.get("disposition")
	if disposition:
		outputs = outputs.filter(disposition=disposition)

	if request.GET.get("process_id"):
		outputs = outputs.filter(related_process_id=request.GET.get("process_id"))

	can_edit = can_edit_nonconforming_output(request.user)
	is_htmx = request.headers.get("HX-Request") == "true"

	context = {
		"outputs": outputs,
		"organization": organization,
		"can_edit": can_edit,
		"processes": Process.objects.filter(
			organization=organization
		).order_by("name"),
		"selected_status": status,
		"selected_severity": severity,
		"selected_disposition": disposition,
		"selected_process_id": request.GET.get("process_id", ""),
	}

	if is_htmx:
		return render(request, "core/pnc/_list_results.html", context)

	return render(
		request,
		"core/nonconforming_output_list.html",
		context,
	)


@login_required
def nonconforming_output_detail(request, pk):
	"""Detalle de Producto/Servicio No Conforme."""
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	output = get_object_or_404(
		NonconformingOutput,
		pk=pk,
		organization=organization,
	)

	can_edit = can_edit_nonconforming_output(request.user)

	return render(
		request,
		"core/nonconforming_output_detail.html",
		{
			"output": output,
			"organization": organization,
			"can_edit": can_edit,
		},
	)


@login_required
def nonconforming_output_create(request):
	"""Crear Producto/Servicio No Conforme."""
	if not can_edit_nonconforming_output(request.user):
		raise PermissionDenied()

	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()

	if request.method == "POST":
		form = NonconformingOutputForm(request.POST, request.FILES)
		if form.is_valid():
			output = form.save(commit=False)
			output.organization = organization
			output.save()
		
			log_audit_event(
				actor=request.user,
				action="core.pnc.created",
				instance=output,
				metadata={
					"code": output.code,
					"product_or_service": output.product_or_service,
					"severity": output.severity,
				},
				object_type_override="NonconformingOutput",
			)
			messages.success(request, f"Producto/Servicio No Conforme {output.code} creado.")
			return redirect("core:nonconforming_output_detail", pk=output.pk)
	else:
		form = NonconformingOutputForm()

	return render(
		request,
		"core/nonconforming_output_form.html",
		{
			"form": form,
			"organization": organization,
			"title": "Nuevo Producto/Servicio No Conforme",
		},
	)


@login_required
def nonconforming_output_edit(request, pk):
	"""Editar Producto/Servicio No Conforme."""
	if not can_edit_nonconforming_output(request.user):
		raise PermissionDenied()

	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	output = get_object_or_404(
		NonconformingOutput,
		pk=pk,
		organization=organization,
	)

	if request.method == "POST":
		form = NonconformingOutputForm(request.POST, request.FILES, instance=output)
		if form.is_valid():
			output = form.save()
			
			log_audit_event(
				actor=request.user,
				action="core.pnc.updated",
				instance=output,
				metadata={
					"code": output.code,
					"status": output.status,
				},
				object_type_override="NonconformingOutput",
			)
			messages.success(request, "Producto/Servicio No Conforme actualizado.")
			return redirect("core:nonconforming_output_detail", pk=output.pk)
	else:
		form = NonconformingOutputForm(instance=output)

	return render(
		request,
		"core/nonconforming_output_form.html",
		{
			"form": form,
			"output": output,
			"organization": organization,
			"title": f"Editar {output.code}",
		},
	)


@login_required
def nonconforming_output_create_nc(request, pk):
	"""Crear NC desde PNC y linkear ambos."""
	if not can_edit_nonconforming_output(request.user):
		raise PermissionDenied()

	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	output = get_object_or_404(
		NonconformingOutput,
		pk=pk,
		organization=organization,
	)

	if output.linked_nc:
		messages.warning(request, "Este PNC ya tiene una NC vinculada.")
		return redirect("core:nonconforming_output_detail", pk=output.pk)

	# Crear NC
	nc = NoConformity.objects.create(
		organization=organization,
		site=output.site,
		related_process=output.related_process,
		title=f"[PNC] {output.product_or_service}",
		description=output.description,
		origin=NoConformity.Origin.PRODUCTION,
		severity=output.severity,
		detected_at=output.detected_at,
		detected_by=output.detected_by,
	)

	# Linkear ambos
	output.linked_nc = nc
	output.save()

	log_audit_event(
		actor=request.user,
		action="core.pnc.nc_created",
		instance=output,
		metadata={
			"pnc_code": output.code,
			"nc_code": nc.code,
		},
		object_type_override="NonconformingOutput",
	)
	
	messages.success(request, f"No Conformidad {nc.code} creada y vinculada a {output.code}.")
	return redirect("core:nonconforming_output_detail", pk=output.pk)


# --- SUPPLIER (ISO 8.4) ---

@login_required
def supplier_list(request):
	"""List suppliers with filtering."""
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	
	suppliers = Supplier.objects.filter(organization=organization).select_related(
		"site", "related_process"
	)
	
	# Filtros
	status_filter = request.GET.get("status", "")
	category_filter = request.GET.get("category", "")
	process_filter = request.GET.get("process", "")
	
	if status_filter:
		suppliers = suppliers.filter(status=status_filter)
	if category_filter:
		suppliers = suppliers.filter(category=category_filter)
	if process_filter:
		suppliers = suppliers.filter(related_process__id=process_filter)
	
	# Agregar dato de evaluación vencida
	suppliers_with_status = []
	for supplier in suppliers:
		suppliers_with_status.append({
			"supplier": supplier,
			"is_overdue": supplier.is_evaluation_overdue,
		})
	
	context = {
		"organization": organization,
		"suppliers_with_status": suppliers_with_status,
		"can_edit": can_edit_supplier(request.user),
		"status_choices": Supplier.Status.choices,
		"category_choices": Supplier.Category.choices,
		"processes": Process.objects.filter(organization=organization),
		"selected_status": status_filter,
		"selected_category": category_filter,
		"selected_process": process_filter,
	}

	if request.headers.get("HX-Request") == "true":
		return render(request, "core/suppliers/_list_results.html", context)

	return render(request, "supplier_list.html", context)


@login_required
def supplier_detail(request, pk):
	"""Show supplier details and evaluations."""
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	
	supplier = get_object_or_404(Supplier, pk=pk, organization=organization)
	
	# Últimas 5 evaluaciones
	evaluations = supplier.evaluations.all()[:5]
	
	context = {
		"organization": organization,
		"supplier": supplier,
		"evaluations": evaluations,
		"is_overdue": supplier.is_evaluation_overdue,
		"can_edit": can_edit_supplier(request.user),
	}
	return render(request, "supplier_detail.html", context)


@login_required
def supplier_create(request):
	"""Create new supplier."""
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	
	if not can_edit_supplier(request.user):
		raise PermissionDenied
	
	if request.method == "POST":
		form = SupplierForm(request.POST)
		if form.is_valid():
			supplier = form.save(commit=False)
			supplier.organization = organization
			supplier.save()
			
			log_audit_event(
				actor=request.user,
				action="core.supplier.created",
				instance=supplier,
				metadata={
					"supplier_id": supplier.id,
					"name": supplier.name,
					"category": supplier.category,
				},
				object_type_override="Supplier",
			)
			
			messages.success(request, f"Proveedor {supplier.name} creado exitosamente.")
			return redirect("core:supplier_detail", pk=supplier.pk)
	else:
		form = SupplierForm()
	
	context = {
		"organization": organization,
		"form": form,
		"title": "Crear Proveedor",
	}
	return render(request, "supplier_form.html", context)


@login_required
def supplier_edit(request, pk):
	"""Edit supplier."""
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	
	supplier = get_object_or_404(Supplier, pk=pk, organization=organization)
	
	if not can_edit_supplier(request.user):
		raise PermissionDenied
	
	if request.method == "POST":
		form = SupplierForm(request.POST, instance=supplier)
		if form.is_valid():
			supplier = form.save()
			
			log_audit_event(
				actor=request.user,
				action="core.supplier.updated",
				instance=supplier,
				metadata={
					"supplier_id": supplier.id,
					"status": supplier.status,
				},
				object_type_override="Supplier",
			)
			
			messages.success(request, f"Proveedor {supplier.name} actualizado.")
			return redirect("core:supplier_detail", pk=supplier.pk)
	else:
		form = SupplierForm(instance=supplier)
	
	context = {
		"organization": organization,
		"form": form,
		"title": f"Editar: {supplier.name}",
		"supplier": supplier,
	}
	return render(request, "supplier_form.html", context)


@login_required
def supplier_evaluation_create(request, supplier_pk):
	"""Create evaluation for supplier."""
	organization = Organization.objects.filter(is_active=True).first() or Organization.objects.first()
	
	supplier = get_object_or_404(Supplier, pk=supplier_pk, organization=organization)
	
	if not can_edit_supplier(request.user):
		raise PermissionDenied
	
	if request.method == "POST":
		form = SupplierEvaluationForm(request.POST, request.FILES)
		if form.is_valid():
			evaluation = form.save(commit=False)
			evaluation.supplier = supplier
			evaluation.organization = organization
			evaluation.evaluator = request.user
			evaluation.save()
			
			log_audit_event(
				actor=request.user,
				action="core.supplier.evaluation.created",
				instance=evaluation,
				metadata={
					"supplier_id": supplier.id,
					"evaluation_date": str(evaluation.evaluation_date),
					"overall_score": str(evaluation.overall_score),
					"decision": evaluation.decision,
				},
				object_type_override="SupplierEvaluation",
			)
			
			messages.success(request, f"Evaluación de {supplier.name} registrada. Puntuación: {evaluation.overall_score}")
			return redirect("core:supplier_detail", pk=supplier.pk)
	else:
		form = SupplierEvaluationForm()
	
	context = {
		"organization": organization,
		"form": form,
		"supplier": supplier,
		"title": f"Evaluar: {supplier.name}",
	}
	return render(request, "supplier_evaluation_form.html", context)


# ============================================================================
# DASHBOARD VIEWS (DASH-01)
# ============================================================================

@login_required
def dashboard_home(request):
	"""Main dashboard view with filters."""
	organization = _get_current_organization()
	if not organization:
		messages.error(request, "No hay organización activa.")
		return redirect("home")
	
	# Get available filters
	sites = Site.objects.filter(organization=organization, is_active=True)
	process_types = Process.ProcessType.choices
	
	# Calculate executive summary metrics
	today = date.today()
	
	# 1. Total open NCs
	total_ncs = NoConformity.objects.filter(
		organization=organization,
		status__in=[NoConformity.Status.OPEN, NoConformity.Status.IN_ANALYSIS, NoConformity.Status.IN_TREATMENT]
	).count()
	
	# 2. Total overdue CAPA actions
	total_capa_overdue = CAPAAction.objects.filter(
		organization=organization,
		status__in=[CAPAAction.Status.OPEN, CAPAAction.Status.IN_PROGRESS],
		due_date__lt=today,
	).count()
	
	# 3. Indicators in target (%)
	all_indicators = QualityIndicator.objects.filter(
		organization=organization,
		is_active=True,
	)
	indicators_in_target = 0
	for ind in all_indicators:
		if ind.get_status() in ["OK"]:
			indicators_in_target += 1
	
	indicators_percentage = 0
	if all_indicators.count() > 0:
		indicators_percentage = int((indicators_in_target / all_indicators.count()) * 100)
	
	# 4. Active suppliers
	active_suppliers = Supplier.objects.filter(
		organization=organization,
		is_active=True,
	).count()
	
	context = {
		"organization": organization,
		"sites": sites,
		"process_types": process_types,
		"title": "Dashboard Ejecutivo ISO",
		# Executive summary
		"summary": {
			"total_ncs": total_ncs,
			"total_capa_overdue": total_capa_overdue,
			"indicators_percentage": indicators_percentage,
			"active_suppliers": active_suppliers,
		}
	}
	return render(request, "dashboard/dashboard.html", context)


@login_required
def dashboard_card_nc(request):
	"""Card: Non-conformities (NC) - open ones."""
	organization = _get_current_organization()
	if not organization:
		return render(request, "core/dashboard/_card_nc.html", {"ncs": [], "count": 0})
	
	# Get filters from request
	site_id = request.GET.get("site_id")
	process_type = request.GET.get("process_type")
	
	# Build queryset (apply filters BEFORE slicing)
	ncs = NoConformity.objects.filter(
		organization=organization,
		status__in=[NoConformity.Status.OPEN, NoConformity.Status.IN_ANALYSIS, NoConformity.Status.IN_TREATMENT]
	).select_related("related_process", "owner").order_by("-updated_at")
	
	if site_id:
		ncs = ncs.filter(site_id=site_id)
	
	if process_type:
		ncs = ncs.filter(related_process__process_type=process_type)
	
	count = ncs.count()
	ncs = ncs[:5]  # Slice AFTER applying all filters
	
	return render(request, "core/dashboard/_card_nc.html", {
		"ncs": ncs,
		"count": count,
	})


@login_required
def dashboard_card_capa(request):
	"""Card: CAPA Actions - overdue ones."""
	organization = _get_current_organization()
	if not organization:
		return render(request, "core/dashboard/_card_capa.html", {"capas": [], "count": 0})
	
	site_id = request.GET.get("site_id")
	process_type = request.GET.get("process_type")
	
	# Get CAPA actions that are overdue (due_date < today and status != DONE)
	today = date.today()
	capas = CAPAAction.objects.filter(
		organization=organization,
		status__in=[CAPAAction.Status.OPEN, CAPAAction.Status.IN_PROGRESS],
		due_date__lt=today,
	).select_related("owner", "no_conformity", "finding").order_by("due_date")[:5]
	
	if site_id:
		# Filter by site if no_conformity exists
		capas = [c for c in capas if c.no_conformity and c.no_conformity.site_id == int(site_id) or c.finding and c.finding.audit.site_id == int(site_id)]
	
	if process_type:
		capas = [c for c in capas if c.no_conformity and c.no_conformity.related_process and c.no_conformity.related_process.process_type == process_type]
	
	count = len(capas)
	
	return render(request, "core/dashboard/_card_capa.html", {
		"capas": capas,
		"count": count,
	})


@login_required
def dashboard_card_indicadores(request):
	"""Card: Quality Indicators - out of target or overdue."""
	organization = _get_current_organization()
	if not organization:
		return render(request, "core/dashboard/_card_indicators.html", {"indicators": [], "count": 0})
	
	site_id = request.GET.get("site_id")
	process_type = request.GET.get("process_type")
	
	# Get indicators with status OUT_OF_TARGET or OVERDUE
	indicators = QualityIndicator.objects.filter(
		organization=organization,
		is_active=True,
	).select_related("related_process")
	
	if site_id:
		# Site is not directly on indicator, skip
		pass
	
	if process_type:
		indicators = indicators.filter(related_process__process_type=process_type)
	
	# Filter by status
	problematic = []
	for ind in indicators:
		status = ind.get_status()
		if status in ["OUT_OF_TARGET", "OVERDUE"]:
			problematic.append((ind, status))
	
	problematic = sorted(problematic, key=lambda x: x[0].name)[:5]
	count = len(problematic)
	
	return render(request, "core/dashboard/_card_indicators.html", {
		"indicators": problematic,
		"count": count,
	})


@login_required
def dashboard_card_pnc(request):
	"""Card: Non-conforming Output (PNC) - open ones."""
	organization = _get_current_organization()
	if not organization:
		return render(request, "core/dashboard/_card_pnc.html", {"pncs": [], "count": 0})
	
	site_id = request.GET.get("site_id")
	process_type = request.GET.get("process_type")
	
	pncs = NonconformingOutput.objects.filter(
		organization=organization,
		status__in=[NonconformingOutput.Status.OPEN, NonconformingOutput.Status.IN_TREATMENT]
	).select_related("related_process").order_by("-detected_at")
	
	if site_id:
		pncs = pncs.filter(site_id=site_id)
	
	if process_type:
		pncs = pncs.filter(related_process__process_type=process_type)
	
	count = pncs.count()
	pncs = pncs[:5]  # Slice AFTER applying all filters
	
	return render(request, "core/dashboard/_card_pnc.html", {
		"pncs": pncs,
		"count": count,
	})


@login_required
def dashboard_card_suppliers(request):
	"""Card: Suppliers with overdue evaluations."""
	organization = _get_current_organization()
	if not organization:
		return render(request, "core/dashboard/_card_suppliers.html", {"suppliers": [], "count": 0})
	
	site_id = request.GET.get("site_id")
	process_type = request.GET.get("process_type")
	
	# Get suppliers with overdue next_evaluation_date
	today = date.today()
	suppliers = Supplier.objects.filter(
		organization=organization,
		next_evaluation_date__isnull=False,
		next_evaluation_date__lt=today,
		is_active=True,
	).order_by("next_evaluation_date")
	
	if site_id:
		suppliers = suppliers.filter(site_id=site_id)
	
	if process_type:
		suppliers = suppliers.filter(related_process__process_type=process_type)
	
	count = suppliers.count()
	suppliers = suppliers[:5]  # Slice AFTER applying all filters
	
	return render(request, "core/dashboard/_card_suppliers.html", {
		"suppliers": suppliers,
		"count": count,
	})


@login_required
def dashboard_card_auditorias(request):
	"""Card: Internal Audits - upcoming in next 30 days."""
	organization = _get_current_organization()
	if not organization:
		return render(request, "core/dashboard/_card_audits.html", {"audits": [], "count": 0})
	
	site_id = request.GET.get("site_id")
	process_type = request.GET.get("process_type")
	
	# Get audits plannned/in progress for next 30 days
	today = date.today()
	next_month = today + timedelta(days=30)
	
	audits = InternalAudit.objects.filter(
		organization=organization,
		status__in=[InternalAudit.Status.PLANNED, InternalAudit.Status.IN_PROGRESS],
		audit_date__gte=today,
		audit_date__lte=next_month,
	).select_related("auditor", "site").order_by("audit_date")
	
	if site_id:
		audits = audits.filter(site_id=site_id)
	
	if process_type:
		# Audits have M2M to related_processes
		audits = audits.filter(related_processes__process_type=process_type).distinct()
	
	count = audits.count()
	audits = audits[:5]  # Slice AFTER applying all filters
	
	return render(request, "core/dashboard/_card_audits.html", {
		"audits": audits,
		"count": count,
	})


@login_required
def dashboard_card_indicators(request):
	"""Alias endpoint (EN): quality indicators card."""
	return dashboard_card_indicadores(request)


@login_required
def dashboard_card_audits(request):
	"""Alias endpoint (EN): audits card."""
	return dashboard_card_auditorias(request)