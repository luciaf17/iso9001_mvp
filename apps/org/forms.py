from django import forms

from apps.core.models import Process


class ProcessForm(forms.ModelForm):
    parent_process = forms.ModelChoiceField(
        queryset=Process.objects.none(),
        required=False,
        label="Proceso padre",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Process
        fields = [
            "organization",
            "site",
            "code",
            "name",
            "process_type",
            "parent_process",
            "level",
            "is_active",
        ]
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "site": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={"class": "form-input"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "process_type": forms.Select(attrs={"class": "form-select"}),
            "level": forms.NumberInput(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent_process"].queryset = Process.objects.order_by("code", "name")
        self.fields["parent_process"].label_from_instance = (
            lambda obj: f"{obj.code} - {obj.name}"
        )

        if self.instance and self.instance.pk:
            self.fields["parent_process"].initial = self.instance.parent
            self.fields["parent_process"].queryset = self.fields["parent_process"].queryset.exclude(
                pk=self.instance.pk
            )

    def clean_parent_process(self):
        parent_process = self.cleaned_data.get("parent_process")
        if self.instance and self.instance.pk and parent_process and parent_process.pk == self.instance.pk:
            raise forms.ValidationError("Un proceso no puede ser padre de sí mismo.")
        return parent_process

    def clean_code(self):
        code = self.cleaned_data.get("code", "")
        return code.strip().upper()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.parent = self.cleaned_data.get("parent_process")
        if commit:
            instance.save()
        return instance
