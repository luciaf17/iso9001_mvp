from django import forms

from apps.core.models import (
    OrganizationContext,
    Process,
    Stakeholder,
    RiskOpportunity,
    NoConformity,
    CAPAAction,
    QualityObjective,
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
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "completion_notes": forms.Textarea(attrs={"rows": 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["due_date"].input_formats = ["%Y-%m-%d"]


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