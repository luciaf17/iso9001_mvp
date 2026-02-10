from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, render

from apps.core.forms import OrganizationContextForm
from apps.core.models import Organization, OrganizationContext, Site
from apps.core.services import log_audit_event
from apps.core.utils import can_edit_context
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
