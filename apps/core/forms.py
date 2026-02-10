from django import forms

from apps.core.models import Process


class ProcessForm(forms.ModelForm):
    class Meta:
        model = Process
        fields = ["code", "name", "process_type", "is_active"]

    def clean_code(self):
        code = self.cleaned_data.get("code", "")
        return code.strip().upper()
