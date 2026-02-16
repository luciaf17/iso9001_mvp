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
            "quality_policy_doc",
            "process_map_doc",
            "org_chart_doc",
            "context_analysis_doc",
        ]
        widgets = {
            "review_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["review_date"].input_formats = ["%Y-%m-%d"]


class StakeholderForm(forms.ModelForm):
    class Meta:
        model = Stakeholder
        fields = [
            "name",
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
            "site",
            "related_process",
            "related_document",
            "title",
            "description",
            "origin",
            "severity",
            "detected_at",
            "detected_by",
            "owner",
            "due_date",
            "status",
            "root_cause_analysis",
            "corrective_action",
            "verification_date",
            "is_effective",
            "verification_notes",
            "evidence_document",
            "closed_date",
            "closed_by",
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