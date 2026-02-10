from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from apps.core.models import AuditEvent, Organization, Process, Site
from apps.docs.models import Document, DocumentVersion
from apps.docs.services import approve_document_version


User = get_user_model()


class ApproveDocumentVersionTests(TestCase):
    def setUp(self):
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

        self.admin = User.objects.create_user(username="admin", password="x")
        self.quality = User.objects.create_user(username="quality", password="x")
        self.reader = User.objects.create_user(username="reader", password="x")

        # Groups (creamos on the fly)
        from django.contrib.auth.models import Group
        g_admin, _ = Group.objects.get_or_create(name="Admin")
        g_quality, _ = Group.objects.get_or_create(name="Calidad")
        g_reader, _ = Group.objects.get_or_create(name="Lectura")

        self.admin.groups.add(g_admin)
        self.quality.groups.add(g_quality)
        self.reader.groups.add(g_reader)

        self.doc = Document.objects.create(
            code="PR-01",
            title="Procedimiento de prueba",
            doc_type=Document.DocType.PROCEDURE,
            owner=self.admin,
        )
        self.doc.processes.add(self.process)

        self.v1 = DocumentVersion.objects.create(
            document=self.doc,
            version_number="1.0",
            file="documents/pr-01-v1.pdf",
            effective_date=timezone.now().date(),
            status=DocumentVersion.Status.APPROVED,
            created_by=self.admin,
        )

        self.v2 = DocumentVersion.objects.create(
            document=self.doc,
            version_number="2.0",
            file="documents/pr-01-v2.pdf",
            effective_date=timezone.now().date(),
            status=DocumentVersion.Status.DRAFT,
            created_by=self.admin,
        )

    def test_approve_sets_only_one_approved_and_obsoletes_previous(self):
        approve_document_version(version_id=self.v2.id, user=self.quality, comment="OK")

        self.v1.refresh_from_db()
        self.v2.refresh_from_db()

        self.assertEqual(self.v2.status, DocumentVersion.Status.APPROVED)
        self.assertEqual(self.v1.status, DocumentVersion.Status.OBSOLETE)

        # Audit event created
        self.assertTrue(AuditEvent.objects.filter(action="docs.version.approved").exists())

        # Approval exists
        self.assertTrue(hasattr(self.v2, "approval"))
        self.assertEqual(self.v2.approval.approved_by, self.quality)

    def test_user_without_permission_cannot_approve(self):
        with self.assertRaises(PermissionDenied):
            approve_document_version(version_id=self.v2.id, user=self.reader)
