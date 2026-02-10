from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.core.models import Organization, Process, Site
from apps.docs.forms import DocumentForm, DocumentVersionForm
from apps.docs.models import Document, DocumentVersion


User = get_user_model()


class DocumentFormTests(TestCase):
	def setUp(self):
		self.owner = User.objects.create_user(username="owner", password="x")
		self.organization = Organization.objects.create(name="Org Test")
		self.site = Site.objects.create(organization=self.organization, name="Site Test")
		self.process = Process.objects.create(
			organization=self.organization,
			site=self.site,
			code="CAL",
			name="Calidad",
			process_type=Process.ProcessType.SUPPORT,
			level=Process.Level.PROCESS,
			is_active=True,
		)

	def test_document_form_normalizes_code(self):
		form = DocumentForm(
			data={
				"code": "  doc-001 ",
				"title": "Manual de Calidad",
				"doc_type": Document.DocType.MANUAL,
				"processes": [self.process.pk],
				"owner": self.owner.pk,
				"is_active": True,
			}
		)

		self.assertTrue(form.is_valid())
		document = form.save()
		self.assertEqual(document.code, "DOC-001")
		self.assertTrue(document.processes.filter(pk=self.process.pk).exists())


class DocumentDetailProcessTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="viewer", password="x")
		self.organization = Organization.objects.create(name="Org Test")
		self.site = Site.objects.create(organization=self.organization, name="Site Test")
		self.process = Process.objects.create(
			organization=self.organization,
			site=self.site,
			code="CAL",
			name="Calidad",
			process_type=Process.ProcessType.SUPPORT,
			level=Process.Level.PROCESS,
			is_active=True,
		)
		self.document = Document.objects.create(
			code="DOC-001",
			title="Manual de Calidad",
			doc_type=Document.DocType.MANUAL,
			owner=self.user,
			is_active=True,
		)
		self.document.processes.add(self.process)

	def test_detail_shows_associated_processes(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse("docs:docs_detail", args=[self.document.pk]))
		self.assertContains(response, "Procesos asociados")
		self.assertContains(response, self.process.code)
		self.assertContains(response, self.process.name)


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

	def test_editing_same_version_does_not_trigger_duplicate_error(self):
		version = DocumentVersion.objects.create(
			document=self.document,
			version_number="1.0",
			file="documents/test.pdf",
			effective_date=date.today(),
			status=DocumentVersion.Status.DRAFT,
			created_by=self.creator,
		)

		form = DocumentVersionForm(
			data={
				"version_number": "1.0",  # mismo número
				"effective_date": date.today(),
				"notes": "Actualización de notas",
			},
			files={"file": self._make_file()},
			instance=version,           # 👈 edición
			document=self.document,
			created_by=self.creator,
		)

		self.assertTrue(form.is_valid(), form.errors)

    
