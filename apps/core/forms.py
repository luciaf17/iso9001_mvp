from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

from apps.core.models import (
    OrganizationContext,
    Process,
    Stakeholder,
    RiskOpportunity,
    NoConformity,
    CAPAAction,
    QualityObjective,
    InternalAudit,
    AuditQuestion,
    AuditAnswer,
    AuditFinding,
    AuditQuestion,
    ManagementReview,
    QualityIndicator,
    IndicatorMeasurement,
    NonconformingOutput,
    Supplier,
    SupplierEvaluation,
    Employee,
    Competency,
    EmployeeCompetency,
    Training,
    TrainingAttendance,
)


class ProcessForm(forms.ModelForm):
    class Meta:
        model = Process
        fields = ["code", "name", "process_type", "is_active"]

    def clean_code(self):
        code = self.cleaned_data.get("code", "")
        return code.strip().upper()


class OrganizationContextForm(forms.ModelForm):
    class Meta:
        model = OrganizationContext
        fields = [
            "site",
            "owner",
            "review_date",
            "summary",
            "qms_scope",
            "quality_policy_doc",
            "process_map_doc",
            "org_chart_doc",
            "context_analysis_doc",
        ]
        widgets = {
            "review_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "qms_scope": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Describa el alcance del Sistema de Gestión de Calidad...",
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["review_date"].input_formats = ["%Y-%m-%d"]


class StakeholderForm(forms.ModelForm):
    class Meta:
        model = Stakeholder
        fields = [
            "name",
            "cuit",
            "phone",
            "stakeholder_type",
            "expectations",
            "related_process",
            "related_document",
            "review_date",
            "is_active",
        ]
        widgets = {
            "review_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "expectations": forms.Textarea(attrs={"rows": 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["review_date"].input_formats = ["%Y-%m-%d"]


class RiskOpportunityForm(forms.ModelForm):
    class Meta:
        model = RiskOpportunity
        fields = [
            "site",
            "related_process",
            "stakeholder",
            "title",
            "description",
            "kind",
            "probability",
            "impact",
            "treatment_plan",
            "owner",
            "due_date",
            "status",
            "evidence_document",
            "is_active",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 4}),
            "treatment_plan": forms.Textarea(attrs={"rows": 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["due_date"].input_formats = ["%Y-%m-%d"]

class NoConformityForm(forms.ModelForm):
    class Meta:
        model = NoConformity
        fields = [
            "detected_at", "related_process", "work_order", "site",
            "observed_during", "norm_clause", "description", "origin",
            "severity", "owner", "detected_by", "organization_representative",
            "due_date",
            "root_cause_analysis", "corrective_action", "closed_date",
            "closed_by", "verification_representative", "evidence_document",
            "verification_date", "status", "is_effective", "verification_notes",
            "title", "classification", "impacts_procedure", "impacts_system",
            "is_active",
        ]
        widgets = {
            "detected_at": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 4}),
            "root_cause_analysis": forms.Textarea(attrs={"rows": 4}),
            "corrective_action": forms.Textarea(attrs={"rows": 4}),
            "verification_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "verification_notes": forms.Textarea(attrs={"rows": 4}),
            "closed_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "work_order": forms.TextInput(attrs={"placeholder": "Ej: Plan Nº 53, OT-2026-001"}),
            "observed_during": forms.TextInput(attrs={"placeholder": "Ej: Control Dimensional, Inspección Final"}),
            "norm_clause": forms.TextInput(attrs={"placeholder": "Ej: ISO 9001:2015 - 8.4"}),
            "impacts_procedure": forms.CheckboxInput(),
            "impacts_system": forms.CheckboxInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar formato de fechas para input type="date"
        self.fields["detected_at"].input_formats = ["%Y-%m-%d"]
        self.fields["due_date"].input_formats = ["%Y-%m-%d"]
        self.fields["verification_date"].input_formats = ["%Y-%m-%d"]
        self.fields["closed_date"].input_formats = ["%Y-%m-%d"]


class CAPAActionForm(forms.ModelForm):
    """Formulario para crear/editar acciones CAPA."""

    class Meta:
        model = CAPAAction
        fields = [
            "title",
            "description",
            "action_type",
            "owner",
            "due_date",
            "status",
            "completion_notes",
            "evidence_document",
            "effectiveness_date",
            "effectiveness_result",
            "effectiveness_notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "completion_notes": forms.Textarea(attrs={"rows": 3}),
            "effectiveness_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "effectiveness_notes": forms.Textarea(attrs={"rows": 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["due_date"].input_formats = ["%Y-%m-%d"]
        self.fields["effectiveness_date"].input_formats = ["%Y-%m-%d"]

    def clean(self):
        cleaned_data = super().clean()
        effectiveness_result = cleaned_data.get("effectiveness_result")
        effectiveness_date = cleaned_data.get("effectiveness_date")

        # Validar que si hay resultado de eficacia, debe haber fecha
        if effectiveness_result and not effectiveness_date:
            raise forms.ValidationError(
                "Si asignas un resultado de eficacia, debes asignar una fecha de evaluacion."
            )

        return cleaned_data
    
    def full_clean(self):
        """Override full_clean to handle model validation that requires parent assignment.
        
        Model.clean() requires no_conformity or finding to be set, but these are assigned
        by the view AFTER form.save(commit=False). So we call full_clean but then remove
        the parent validation error if it was added.
        """
        super().full_clean()
        
        # Remove the parent-related validation error from non-field errors if it exists
        # It will be validated properly in the view after parent assignment
        if "__all__" in self.errors:
            new_errors = []
            for error in self.errors["__all__"]:
                error_msg = str(error)
                if "vinculada" not in error_msg and "linked" not in error_msg:
                    new_errors.append(error)
            
            if new_errors:
                self.add_error(None, new_errors)
            else:
                # Remove the non-field error key if no errors remain
                if "__all__" in self.errors:
                    del self.errors["__all__"]


class QualityObjectiveForm(forms.ModelForm):
    """Formulario para crear/editar objetivos de calidad."""

    class Meta:
        model = QualityObjective
        fields = [
            "site",
            "related_process",
            "title",
            "description",
            "indicator",
            "target_value",
            "current_value",
            "unit",
            "frequency",
            "owner",
            "start_date",
            "due_date",
            "is_active",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 4}),
            "target_value": forms.NumberInput(attrs={"step": "0.01"}),
            "current_value": forms.NumberInput(attrs={"step": "0.01"}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que las fechas usen el formato correcto para input type="date"
        self.fields["start_date"].input_formats = ["%Y-%m-%d"]
        self.fields["due_date"].input_formats = ["%Y-%m-%d"]


class InternalAuditForm(forms.ModelForm):
    """Formulario para crear/editar auditorias internas."""

    class Meta:
        model = InternalAudit
        fields = [
            "site",
            "title",
            "audit_date",
            "audit_type",
            "scope",
            "auditor",
            "auditee",
            "status",
            "related_processes",
            "evidence_document",
            "plan_file",
            "report_file",
            "team_cv_file",
        ]
        widgets = {
            "audit_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "scope": forms.Textarea(attrs={"rows": 3}),
            "related_processes": forms.SelectMultiple(attrs={"size": 6}),
            "plan_file": forms.ClearableFileInput(),
            "report_file": forms.ClearableFileInput(),
            "team_cv_file": forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["audit_date"].input_formats = ["%Y-%m-%d"]

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate PDF files
        files_to_check = {
            "plan_file": "Archivo de planificación",
            "report_file": "Archivo de informe",
            "team_cv_file": "CV del equipo auditor",
        }
        
        for field_name, field_label in files_to_check.items():
            uploaded_file = cleaned_data.get(field_name)
            if uploaded_file:
                # Check extension
                if not uploaded_file.name.lower().endswith(".pdf"):
                    self.add_error(field_name, f"{field_label} debe ser un archivo PDF.")
                # Check MIME type
                elif uploaded_file.content_type != "application/pdf":
                    self.add_error(field_name, f"{field_label} debe ser un archivo PDF válido.")
        
        return cleaned_data


AuditAnswerFormSet = inlineformset_factory(
    InternalAudit,
    AuditAnswer,
    fields=["question", "result", "notes"],
    extra=0,
    can_delete=False,
    widgets={
        "notes": forms.Textarea(attrs={"rows": 2}),
    },
)


class AuditFindingForm(forms.ModelForm):
    """Formulario para crear/editar hallazgos de auditoria."""

    class Meta:
        model = AuditFinding
        fields = [
            "related_process",
            "finding_type",
            "description",
            "severity",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class AuditQuestionForm(forms.ModelForm):
    """Formulario para crear/editar preguntas de auditoria."""

    class Meta:
        model = AuditQuestion
        fields = [
            "process_type",
            "text",
            "ordering",
            "is_active",
        ]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 3}),
            "ordering": forms.NumberInput(),
        }


class ManagementReviewForm(forms.ModelForm):
    """Formulario para crear/editar revisiones por la direccion."""

    class Meta:
        model = ManagementReview
        fields = [
            "review_date",
            "chairperson",
            "attendees",
            "audit_results_summary",
            "customer_feedback_summary",
            "process_performance_summary",
            "nonconformities_status_summary",
            "risk_opportunity_status_summary",
            "supplier_performance_summary",
            "resource_adequacy_summary",
            "improvement_actions",
            "changes_to_qms",
            "resource_needs",
            "meeting_minutes_file",
        ]
        widgets = {
            "review_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "attendees": forms.Textarea(attrs={"rows": 3}),
            "audit_results_summary": forms.Textarea(attrs={"rows": 3}),
            "customer_feedback_summary": forms.Textarea(attrs={"rows": 3}),
            "process_performance_summary": forms.Textarea(attrs={"rows": 3}),
            "nonconformities_status_summary": forms.Textarea(attrs={"rows": 3}),
            "risk_opportunity_status_summary": forms.Textarea(attrs={"rows": 3}),
            "supplier_performance_summary": forms.Textarea(attrs={"rows": 3}),
            "resource_adequacy_summary": forms.Textarea(attrs={"rows": 3}),
            "improvement_actions": forms.Textarea(attrs={"rows": 3}),
            "changes_to_qms": forms.Textarea(attrs={"rows": 3}),
            "resource_needs": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["review_date"].input_formats = ["%Y-%m-%d"]


class QualityIndicatorForm(forms.ModelForm):
    """Formulario para crear/editar indicadores de calidad."""

    class Meta:
        model = QualityIndicator
        fields = [
            "name",
            "description",
            "related_process",
            "frequency",
            "target_value",
            "comparison_type",
            "unit",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "target_value": forms.NumberInput(attrs={"step": "0.01"}),
        }


class IndicatorMeasurementForm(forms.ModelForm):
    """Formulario para registrar mediciones de indicadores."""

    class Meta:
        model = IndicatorMeasurement
        fields = [
            "measurement_date",
            "value",
            "notes",
        ]
        widgets = {
            "measurement_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "value": forms.NumberInput(attrs={"step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["measurement_date"].input_formats = ["%Y-%m-%d"]


class NonconformingOutputForm(forms.ModelForm):
    """Formulario para Producto/Servicio No Conforme (ISO 8.7)."""

    class Meta:
        model = NonconformingOutput
        fields = [
            "detected_at", "related_process", "work_order", "site",
            "observed_during", "norm_clause", "description", "product_or_service",
            "severity", "owner", "detected_by", "organization_representative",
            "root_cause_analysis", "corrective_action",
            "quantity", "disposition", "disposition_notes", "responsible",
            "closed_at", "verification_representative", "evidence_file", "linked_nc",
            "verification_date", "status", "verification_notes",
            "title", "classification", "impacts_procedure", "impacts_system",
            "is_active",
        ]
        widgets = {
            "detected_at": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "closed_at": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "verification_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 4}),
            "root_cause_analysis": forms.Textarea(attrs={"rows": 4}),
            "corrective_action": forms.Textarea(attrs={"rows": 4}),
            "verification_notes": forms.Textarea(attrs={"rows": 4}),
            "disposition_notes": forms.Textarea(attrs={"rows": 3}),
            "quantity": forms.NumberInput(attrs={"step": "0.01"}),
            "work_order": forms.TextInput(attrs={"placeholder": "Ej: Plan Nº 53, OT-2026-001"}),
            "observed_during": forms.TextInput(attrs={"placeholder": "Ej: Control Dimensional, Inspección Final"}),
            "norm_clause": forms.TextInput(attrs={"placeholder": "Ej: ISO 9001:2015 - 8.4"}),
            "impacts_procedure": forms.CheckboxInput(),
            "impacts_system": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["detected_at"].input_formats = ["%Y-%m-%d"]
        self.fields["closed_at"].input_formats = ["%Y-%m-%d"]
        self.fields["verification_date"].input_formats = ["%Y-%m-%d"]


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "site",
            "related_process",
            "name",
            "cuit",
            "category",
            "contact_name",
            "contact_email",
            "contact_phone",
            "next_evaluation_date",
            "is_active",
        ]
        widgets = {
            "next_evaluation_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "name": forms.TextInput(attrs={"placeholder": "Nombre del Proveedor"}),
            "contact_name": forms.TextInput(attrs={"placeholder": "Ej: Juan Pérez"}),
            "contact_email": forms.EmailInput(attrs={"placeholder": "correo@proveedor.com"}),
            "contact_phone": forms.TextInput(attrs={"placeholder": "+54 9 11 1234-5678"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["next_evaluation_date"].input_formats = ["%Y-%m-%d"]


class SupplierEvaluationForm(forms.ModelForm):
    class Meta:
        model = SupplierEvaluation
        fields = [
            "evaluation_date",
            "quality_score",
            "delivery_score",
            "price_score",
            "decision",
            "notes",
            "evidence_file",
        ]
        widgets = {
            "evaluation_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "quality_score": forms.NumberInput(attrs={"min": "1", "max": "5", "type": "number"}),
            "delivery_score": forms.NumberInput(attrs={"min": "1", "max": "5", "type": "number"}),
            "price_score": forms.NumberInput(attrs={"min": "1", "max": "5", "type": "number"}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Observaciones de la evaluación"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["evaluation_date"].input_formats = ["%Y-%m-%d"]
        self.fields["quality_score"].help_text = "1=Muy malo, 5=Excelente"
        self.fields["delivery_score"].help_text = "1=Muy malo, 5=Excelente"
        self.fields["price_score"].help_text = "1=Muy caro, 5=Muy competitivo"


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "first_name",
            "last_name",
            "position",
            "department",
            "email",
            "is_active",
        ]


class CompetencyForm(forms.ModelForm):
    class Meta:
        model = Competency
        fields = [
            "name",
            "description",
            "required_for_position",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class TrainingForm(forms.ModelForm):
    class Meta:
        model = Training
        fields = [
            "title",
            "description",
            "provider",
            "training_date",
            "expiration_date",
            "evidence_file",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "training_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "expiration_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["training_date"].input_formats = ["%Y-%m-%d"]
        self.fields["expiration_date"].input_formats = ["%Y-%m-%d"]


class TrainingAttendanceForm(forms.ModelForm):
    class Meta:
        model = TrainingAttendance
        fields = [
            "training",
            "employee",
            "completion_status",
            "effectiveness_evaluated",
            "effectiveness_result",
            "evaluation_date",
            "notes",
        ]
        widgets = {
            "completion_status": forms.Select(),
            "effectiveness_result": forms.Select(),
            "evaluation_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["evaluation_date"].input_formats = ["%Y-%m-%d"]


class EmployeeCompetencyForm(forms.ModelForm):
    class Meta:
        model = EmployeeCompetency
        fields = [
            "competency",
            "level_required",
            "level_current",
            "last_evaluated",
        ]
        widgets = {
            "last_evaluated": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop("employee", None)
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        
        if organization:
            # Only show competencies from this organization
            self.fields["competency"].queryset = Competency.objects.filter(
                organization=organization
            )
        
        if employee:
            # Exclude already assigned competencies
            assigned_competency_ids = EmployeeCompetency.objects.filter(
                employee=employee
            ).values_list("competency_id", flat=True)
            self.fields["competency"].queryset = self.fields["competency"].queryset.exclude(
                id__in=assigned_competency_ids
            )
        
        self.fields["last_evaluated"].input_formats = ["%Y-%m-%d"]


class ManagementReviewForm(forms.ModelForm):
    class Meta:
        model = ManagementReview
        fields = [
            "review_date",
            "chairperson",
            "attendees",
            "audit_results_summary",
            "customer_feedback_summary",
            "process_performance_summary",
            "nonconformities_status_summary",
            "risk_opportunity_status_summary",
            "supplier_performance_summary",
            "resource_adequacy_summary",
            "improvement_actions",
            "changes_to_qms",
            "resource_needs",
            "meeting_minutes_file",
        ]
        widgets = {
            "review_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "attendees": forms.Textarea(attrs={"rows": 2}),
            "audit_results_summary": forms.Textarea(attrs={"rows": 3}),
            "customer_feedback_summary": forms.Textarea(attrs={"rows": 3}),
            "process_performance_summary": forms.Textarea(attrs={"rows": 3}),
            "nonconformities_status_summary": forms.Textarea(attrs={"rows": 3}),
            "risk_opportunity_status_summary": forms.Textarea(attrs={"rows": 3}),
            "supplier_performance_summary": forms.Textarea(attrs={"rows": 3}),
            "resource_adequacy_summary": forms.Textarea(attrs={"rows": 3}),
            "improvement_actions": forms.Textarea(attrs={"rows": 3}),
            "changes_to_qms": forms.Textarea(attrs={"rows": 3}),
            "resource_needs": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["review_date"].input_formats = ["%Y-%m-%d"]