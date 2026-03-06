from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.forms import (
    CompetencyForm,
    EmployeeForm,
    EmployeeCompetencyForm,
    TrainingAttendanceForm,
    TrainingForm,
)
from apps.core.models import (
    Competency,
    Employee,
    EmployeeCompetency,
    Organization,
    Training,
    TrainingAttendance,
)
from apps.core.services import log_audit_event
from apps.core.utils import can_edit_competency_training


def _get_current_organization():
    return Organization.objects.filter(is_active=True).first() or Organization.objects.first()


def _configure_attendance_form(form, organization):
    form.fields["training"].queryset = Training.objects.filter(organization=organization).order_by("-training_date")
    form.fields["employee"].queryset = Employee.objects.filter(organization=organization, is_active=True).order_by("last_name", "first_name")


@login_required
def employee_list(request):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    employees = Employee.objects.filter(organization=organization).order_by("last_name", "first_name")

    search = request.GET.get("search", "").strip()
    department = request.GET.get("department", "").strip()
    is_active = request.GET.get("is_active", "")

    if search:
        employees = employees.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(position__icontains=search)
            | Q(email__icontains=search)
        )

    if department:
        employees = employees.filter(department__icontains=department)

    if is_active in ["true", "false"]:
        employees = employees.filter(is_active=(is_active == "true"))

    return render(
        request,
        "core/competencies/employee_list.html",
        {
            "organization": organization,
            "employees": employees,
            "can_edit": can_edit_competency_training(request.user),
            "selected_search": search,
            "selected_department": department,
            "selected_is_active": is_active,
        },
    )


@login_required
def employee_detail(request, pk):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    employee = get_object_or_404(Employee, pk=pk, organization=organization)
    competencies = (
        EmployeeCompetency.objects.filter(employee=employee)
        .select_related("competency")
        .order_by("competency__name")
    )
    attendances = (
        TrainingAttendance.objects.filter(employee=employee)
        .select_related("training")
        .order_by("-training__training_date")[:10]
    )

    return render(
        request,
        "core/competencies/employee_detail.html",
        {
            "organization": organization,
            "employee": employee,
            "competencies": competencies,
            "attendances": attendances,
            "gap_count": competencies.filter(is_gap=True).count(),
            "can_edit": can_edit_competency_training(request.user),
        },
    )


@login_required
def employee_add_competency(request, pk):
    """Asignar competencia a un empleado (GET: form, POST: guardar)."""
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    if not can_edit_competency_training(request.user):
        raise PermissionDenied

    employee = get_object_or_404(Employee, pk=pk, organization=organization)

    if request.method == "POST":
        form = EmployeeCompetencyForm(
            request.POST,
            employee=employee,
            organization=organization,
        )
        if form.is_valid():
            employee_competency = form.save(commit=False)
            employee_competency.employee = employee
            employee_competency.calculate_gap()
            employee_competency.save()

            log_audit_event(
                actor=request.user,
                action="core.employee.competency_assigned",
                instance=employee_competency,
                metadata={
                    "organization_id": organization.id,
                    "employee_id": employee.id,
                    "competency_id": employee_competency.competency_id,
                    "details": f"Competencia '{employee_competency.competency.name}' asignada a {employee.first_name} {employee.last_name}",
                },
                object_type_override="EmployeeCompetency",
            )

            messages.success(request, "Competencia asignada correctamente.")

            # Return updated competency table for HTMX
            competencies = (
                EmployeeCompetency.objects.filter(employee=employee)
                .select_related("competency")
                .order_by("competency__name")
            )
            return render(
                request,
                "core/competencies/_competency_table.html",
                {
                    "competencies": competencies,
                },
            )
        else:
            response = render(
                request,
                "core/competencies/_add_competency_form.html",
                {
                    "form": form,
                    "employee": employee,
                },
            )
            response["HX-Retarget"] = "#competency-modal-content"
            response.status_code = 422
            return response
    else:
        # GET: Show form
        form = EmployeeCompetencyForm(
            employee=employee,
            organization=organization,
        )
        return render(
            request,
            "core/competencies/_add_competency_form.html",
            {
                "form": form,
                "employee": employee,
            },
        )


@login_required
def employee_create(request):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    if not can_edit_competency_training(request.user):
        raise PermissionDenied

    form = EmployeeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        employee = form.save(commit=False)
        employee.organization = organization
        employee.save()

        log_audit_event(
            actor=request.user,
            action="core.employee.created",
            instance=employee,
            metadata={
                "employee_id": employee.id,
                "position": employee.position,
            },
            object_type_override="Employee",
        )

        messages.success(request, "Empleado creado correctamente.")
        return redirect("core:employee_detail", pk=employee.pk)

    return render(
        request,
        "core/competencies/employee_form.html",
        {
            "organization": organization,
            "form": form,
            "title": "Nuevo Empleado",
            "is_edit": False,
        },
    )


@login_required
def employee_edit(request, pk):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    if not can_edit_competency_training(request.user):
        raise PermissionDenied

    employee = get_object_or_404(Employee, pk=pk, organization=organization)
    form = EmployeeForm(request.POST or None, instance=employee)

    if request.method == "POST" and form.is_valid():
        employee = form.save()

        log_audit_event(
            actor=request.user,
            action="core.employee.updated",
            instance=employee,
            metadata={
                "employee_id": employee.id,
                "is_active": employee.is_active,
            },
            object_type_override="Employee",
        )

        messages.success(request, "Empleado actualizado correctamente.")
        return redirect("core:employee_detail", pk=employee.pk)

    return render(
        request,
        "core/competencies/employee_form.html",
        {
            "organization": organization,
            "form": form,
            "employee": employee,
            "title": f"Editar {employee.first_name} {employee.last_name}",
            "is_edit": True,
        },
    )


@login_required
def competency_list(request):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    competencies = Competency.objects.filter(organization=organization).order_by("name")

    search = request.GET.get("search", "").strip()
    position = request.GET.get("position", "").strip()

    if search:
        competencies = competencies.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if position:
        competencies = competencies.filter(required_for_position__icontains=position)

    return render(
        request,
        "core/competencies/competency_list.html",
        {
            "organization": organization,
            "competencies": competencies,
            "can_edit": can_edit_competency_training(request.user),
            "selected_search": search,
            "selected_position": position,
        },
    )


@login_required
def competency_create(request):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    if not can_edit_competency_training(request.user):
        raise PermissionDenied

    form = CompetencyForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        competency = form.save(commit=False)
        competency.organization = organization
        competency.save()
        messages.success(request, "Competencia creada correctamente.")
        return redirect("core:competency_list")

    return render(
        request,
        "core/competencies/competency_form.html",
        {
            "organization": organization,
            "form": form,
            "title": "Nueva Competencia",
            "is_edit": False,
        },
    )


@login_required
def competency_edit(request, pk):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    if not can_edit_competency_training(request.user):
        raise PermissionDenied

    competency = get_object_or_404(Competency, pk=pk, organization=organization)
    form = CompetencyForm(request.POST or None, instance=competency)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Competencia actualizada correctamente.")
        return redirect("core:competency_list")

    return render(
        request,
        "core/competencies/competency_form.html",
        {
            "organization": organization,
            "form": form,
            "competency": competency,
            "title": f"Editar {competency.name}",
            "is_edit": True,
        },
    )


@login_required
def training_list(request):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    trainings = Training.objects.filter(organization=organization).order_by("-training_date")

    search = request.GET.get("search", "").strip()
    provider = request.GET.get("provider", "").strip()

    if search:
        trainings = trainings.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if provider:
        trainings = trainings.filter(provider__icontains=provider)

    return render(
        request,
        "core/competencies/training_list.html",
        {
            "organization": organization,
            "trainings": trainings,
            "can_edit": can_edit_competency_training(request.user),
            "selected_search": search,
            "selected_provider": provider,
        },
    )


@login_required
def training_detail(request, pk):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    training = get_object_or_404(Training, pk=pk, organization=organization)
    attendances = (
        TrainingAttendance.objects.filter(training=training)
        .select_related("employee")
        .order_by("employee__last_name", "employee__first_name")
    )

    return render(
        request,
        "core/competencies/training_detail.html",
        {
            "organization": organization,
            "training": training,
            "attendances": attendances,
            "can_edit": can_edit_competency_training(request.user),
        },
    )


@login_required
def training_create(request):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    if not can_edit_competency_training(request.user):
        raise PermissionDenied

    form = TrainingForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        training = form.save(commit=False)
        training.organization = organization
        training.save()

        log_audit_event(
            actor=request.user,
            action="core.training.created",
            instance=training,
            metadata={
                "training_id": training.id,
                "provider": training.provider,
            },
            object_type_override="Training",
        )

        messages.success(request, "Capacitación creada correctamente.")
        return redirect("core:training_detail", pk=training.pk)

    return render(
        request,
        "core/competencies/training_form.html",
        {
            "organization": organization,
            "form": form,
            "title": "Nueva Capacitación",
            "is_edit": False,
        },
    )


@login_required
def training_edit(request, pk):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    if not can_edit_competency_training(request.user):
        raise PermissionDenied

    training = get_object_or_404(Training, pk=pk, organization=organization)
    form = TrainingForm(request.POST or None, request.FILES or None, instance=training)

    if request.method == "POST" and form.is_valid():
        training = form.save()
        messages.success(request, "Capacitación actualizada correctamente.")
        return redirect("core:training_detail", pk=training.pk)

    return render(
        request,
        "core/competencies/training_form.html",
        {
            "organization": organization,
            "form": form,
            "training": training,
            "title": f"Editar {training.title}",
            "is_edit": True,
        },
    )


@login_required
def training_attendance_create(request):
    organization = _get_current_organization()
    if not organization:
        messages.error(request, "No hay organización activa.")
        return redirect("home")

    if not can_edit_competency_training(request.user):
        raise PermissionDenied

    form = TrainingAttendanceForm(request.POST or None)
    _configure_attendance_form(form, organization)

    if request.method == "POST" and form.is_valid():
        attendance = form.save()

        if attendance.completion_status == TrainingAttendance.CompletionStatus.COMPLETED:
            log_audit_event(
                actor=request.user,
                action="core.training.completed",
                instance=attendance,
                metadata={
                    "training_id": attendance.training_id,
                    "employee_id": attendance.employee_id,
                },
                object_type_override="TrainingAttendance",
            )

        if attendance.effectiveness_evaluated and attendance.effectiveness_result:
            log_audit_event(
                actor=request.user,
                action="core.training.effectiveness_evaluated",
                instance=attendance,
                metadata={
                    "training_id": attendance.training_id,
                    "employee_id": attendance.employee_id,
                    "result": attendance.effectiveness_result,
                    "evaluation_date": str(attendance.evaluation_date) if attendance.evaluation_date else None,
                },
                object_type_override="TrainingAttendance",
            )

        messages.success(request, "Asistencia de capacitación registrada correctamente.")
        return redirect("core:training_detail", pk=attendance.training_id)

    return render(
        request,
        "core/competencies/training_attendance_form.html",
        {
            "organization": organization,
            "form": form,
            "title": "Registrar Asistencia de Capacitación",
        },
    )


@login_required
def dashboard_card_competencies(request):
    """Card dashboard: employees with competency gaps."""
    organization = _get_current_organization()
    if not organization:
        return render(request, "core/dashboard/_card_competencies.html", {"rows": [], "count": 0})

    gaps = (
        EmployeeCompetency.objects.filter(
            employee__organization=organization,
            employee__is_active=True,
            is_gap=True,
        )
        .select_related("employee", "competency")
        .order_by("employee__last_name", "employee__first_name", "competency__name")
    )

    count = gaps.count()
    rows = gaps[:5]

    return render(
        request,
        "core/dashboard/_card_competencies.html",
        {
            "rows": rows,
            "count": count,
        },
    )
