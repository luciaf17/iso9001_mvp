from django import forms

from apps.core.models import OrganizationContext, Process


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
