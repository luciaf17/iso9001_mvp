from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.models import Process
from apps.docs.forms import DocumentForm, DocumentVersionForm
from apps.docs.models import Document, DocumentVersion


User = get_user_model()


class DocumentFormTests(TestCase):
	def setUp(self):
		self.owner = User.objects.create_user(username="owner", password="x")
		self.process = Process.objects.create(code="CAL", name="Calidad")

	def test_document_form_normalizes_code(self):
		form = DocumentForm(
			data={
				"code": "  doc-001 ",
				"title": "Manual de Calidad",
				"doc_type": Document.DocType.MANUAL,
				"process": self.process.pk,
				"owner": self.owner.pk,
				"is_active": True,
			}
		)

		self.assertTrue(form.is_valid())
		document = form.save()
		self.assertEqual(document.code, "DOC-001")


class DocumentVersionFormTests(TestCase):
	def setUp(self):
		self.owner = User.objects.create_user(username="owner", password="x")
		self.creator = User.objects.create_user(username="creator", password="x")
		self.document = Document.objects.create(
			code="DOC-001",
			title="Manual de Calidad",
			doc_type=Document.DocType.MANUAL,
			owner=self.owner,
			is_active=True,
		)

	def _make_file(self):
		return SimpleUploadedFile(
			"test.pdf",
			b"%PDF-1.4 test file content",
			content_type="application/pdf",
		)

	def test_version_form_requires_document_and_created_by(self):
		with self.assertRaisesMessage(ValueError, "document es obligatorio"):
			DocumentVersionForm(data={})

		with self.assertRaisesMessage(ValueError, "created_by es obligatorio"):
			DocumentVersionForm(document=self.document, data={})

	def test_version_form_validates_review_date(self):
		form = DocumentVersionForm(
			data={
				"version_number": "1.0",
				"effective_date": date.today(),
				"review_due_date": date.today() - timedelta(days=1),
				"notes": "",
			},
			files={"file": self._make_file()},
			document=self.document,
			created_by=self.creator,
		)

		self.assertFalse(form.is_valid())
		self.assertIn("review_due_date", form.errors)

	def test_version_form_prevents_duplicate_version(self):
		DocumentVersion.objects.create(
			document=self.document,
			version_number="1.0",
			file="documents/test.pdf",
			effective_date=date.today(),
			status=DocumentVersion.Status.DRAFT,
			created_by=self.creator,
		)

		form = DocumentVersionForm(
			data={
				"version_number": "1.0",
				"effective_date": date.today(),
				"notes": "",
			},
			files={"file": self._make_file()},
			document=self.document,
			created_by=self.creator,
		)

		self.assertFalse(form.is_valid())
		self.assertIn("version_number", form.errors)

	def test_version_form_sets_document_and_created_by(self):
		form = DocumentVersionForm(
			data={
				"version_number": " 1.0 ",
				"effective_date": date.today(),
				"notes": "",
			},
			files={"file": self._make_file()},
			document=self.document,
			created_by=self.creator,
		)

		self.assertTrue(form.is_valid())
		version = form.save()
		self.assertEqual(version.document, self.document)
		self.assertEqual(version.created_by, self.creator)
		self.assertEqual(version.version_number, "1.0")
