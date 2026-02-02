from django import forms

from .models import Document, DocumentVersion


class DocumentForm(forms.ModelForm):
	"""Formulario para crear/editar documentos."""

	class Meta:
		model = Document
		fields = ["code", "title", "doc_type", "process", "owner", "is_active"]

	def clean_code(self):
		code = self.cleaned_data.get("code", "")
		normalized = code.strip().upper()
		if not normalized:
			raise forms.ValidationError("El código del documento es obligatorio.")
		return normalized


class DocumentVersionForm(forms.ModelForm):
	"""Formulario para subir versiones de documentos."""

	class Meta:
		model = DocumentVersion
		fields = ["version_number", "file", "effective_date", "review_due_date", "notes"]

	def __init__(self, *args, document=None, created_by=None, **kwargs):
		if document is None:
			raise ValueError("document es obligatorio para DocumentVersionForm")
		if created_by is None:
			raise ValueError("created_by es obligatorio para DocumentVersionForm")
		super().__init__(*args, **kwargs)
		self.document = document
		self.created_by = created_by

	def clean_version_number(self):
		version_number = self.cleaned_data.get("version_number", "")
		normalized = version_number.strip()
		if not normalized:
			raise forms.ValidationError("El número de versión es obligatorio.")
		return normalized

	def clean(self):
		cleaned_data = super().clean()
		effective_date = cleaned_data.get("effective_date")
		review_due_date = cleaned_data.get("review_due_date")

		if effective_date and review_due_date and review_due_date < effective_date:
			self.add_error(
				"review_due_date",
				"La fecha de revisión no puede ser anterior a la fecha de vigencia.",
			)

		version_number = cleaned_data.get("version_number")
		if version_number:
			qs = DocumentVersion.objects.filter(document=self.document, version_number=version_number)
			if self.instance.pk:
				qs = qs.exclude(pk=self.instance.pk)
			if qs.exists():
				self.add_error("version_number", "Ya existe una versión con ese número para este documento.")

		return cleaned_data

	def save(self, commit=True):
		instance = super().save(commit=False)
		instance.document = self.document
		instance.created_by = self.created_by
		if commit:
			instance.save()
		return instance
