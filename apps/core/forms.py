from django import forms

from apps.core.models import OrganizationContext, Process, Stakeholder, RiskOpportunity, NoConformity


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
            "review_date": forms.DateInput(attrs={"type": "date"}),
        }


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
            "review_date": forms.DateInput(attrs={"type": "date"}),
            "expectations": forms.Textarea(attrs={"rows": 4}),
        }


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
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "treatment_plan": forms.Textarea(attrs={"rows": 4}),
        }

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
            "owner",
            "due_date",
            "status",
            "evidence_document",
            "is_active",
        ]
        widgets = {
            "detected_at": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }