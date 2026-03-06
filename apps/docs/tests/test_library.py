from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Group

from apps.core.models import Organization, Site, Process
from apps.docs.models import Document, DocumentVersion

User = get_user_model()


class DocsLibraryViewTests(TestCase):
    def setUp(self):
        """Configurar datos de prueba con jerarquía de procesos y documentos."""
        # Organización y sede
        self.org = Organization.objects.create(name="Test Corp")
        self.site = Site.objects.create(organization=self.org, name="Sede Central")
        
        # Procesos nivel 1
        self.process_l1_strategic = Process.objects.create(
            organization=self.org,
            site=self.site,
            code="ESTRAT",
            name="Procesos Estratégicos",
            process_type=Process.ProcessType.STRATEGIC,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        self.process_l1_missional = Process.objects.create(
            organization=self.org,
            site=self.site,
            code="MISIO",
            name="Procesos Misionales",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.PROCESS,
            is_active=True,
        )
        
        # Subproceso (nivel 2) bajo MISSIONAL
        self.process_l2_production = Process.objects.create(
            organization=self.org,
            site=self.site,
            code="MISIO.01",
            name="Producción",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.SUBPROCESS,
            parent=self.process_l1_missional,
            is_active=True,
        )
        
        # Sector (nivel 3) bajo PRODUCCIÓN
        self.process_l3_quality = Process.objects.create(
            organization=self.org,
            site=self.site,
            code="MISIO.01.01",
            name="Control de Calidad",
            process_type=Process.ProcessType.MISSIONAL,
            level=Process.Level.SECTOR,
            parent=self.process_l2_production,
            is_active=True,
        )
        
        # Usuarios
        self.user = User.objects.create_user(username="testuser", password="test123")
        group, _ = Group.objects.get_or_create(name="Lectura")
        self.user.groups.add(group)
        
        self.client = Client()
        self.client.login(username="testuser", password="test123")
        
        # Documentos
        self.doc_l1 = Document.objects.create(
            code="DOC-001",
            title="Manual de Procesos Estratégicos",
            doc_type=Document.DocType.MANUAL,
            owner=self.user,
            is_active=True,
        )
        self.doc_l1.processes.add(self.process_l1_strategic)
        
        self.doc_l2 = Document.objects.create(
            code="DOC-002",
            title="Procedimiento de Producción",
            doc_type=Document.DocType.PROCEDURE,
            owner=self.user,
            is_active=True,
        )
        self.doc_l2.processes.add(self.process_l2_production)
        
        self.doc_l3 = Document.objects.create(
            code="DOC-003",
            title="Formato de Control de Calidad",
            doc_type=Document.DocType.FORMAT,
            owner=self.user,
            is_active=True,
        )
        self.doc_l3.processes.add(self.process_l3_quality)
        
        # Versión aprobada para doc_l1
        self.v1_approved = DocumentVersion.objects.create(
            document=self.doc_l1,
            version_number="1.0",
            file="test.pdf",
            effective_date="2024-01-01",
            status=DocumentVersion.Status.APPROVED,
            created_by=self.user,
        )
        
        # Versión aprobada para doc_l2
        self.v2_approved = DocumentVersion.objects.create(
            document=self.doc_l2,
            version_number="2.0",
            file="test.pdf",
            effective_date="2024-01-15",
            status=DocumentVersion.Status.APPROVED,
            created_by=self.user,
        )
        
        # doc_l3 sin versión aprobada (solo draft)
        self.v3_draft = DocumentVersion.objects.create(
            document=self.doc_l3,
            version_number="0.1",
            file="test.pdf",
            effective_date="2024-02-01",
            status=DocumentVersion.Status.DRAFT,
            created_by=self.user,
        )
    
    def test_library_view_requires_login(self):
        """La vista debe requerir login."""
        self.client.logout()
        response = self.client.get(reverse("docs:docs_library"))
        self.assertEqual(response.status_code, 302)  # Redirect a login
    
    def test_library_view_loads_successfully(self):
        """La vista debe cargar exitosamente."""
        response = self.client.get(reverse("docs:docs_library"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "docs/docs_library.html")
    
    def test_library_lists_processes_and_documents(self):
        """La vista debe mostrar procesos con sus documentos."""
        response = self.client.get(reverse("docs:docs_library"))
        self.assertEqual(response.status_code, 200)
        
        # Verificar que los procesos level 1 están en el contexto
        processes = response.context["processes"]
        self.assertEqual(len(processes), 2)
        
        # Verificar que contiene los procesos esperados
        process_codes = [p.code for p in processes]
        self.assertIn("ESTRAT", process_codes)
        self.assertIn("MISIO", process_codes)
    
    def test_library_shows_only_approved_versions(self):
        """Solo documentos con versión APPROVED deben mostrarse."""
        response = self.client.get(reverse("docs:docs_library"))
        self.assertEqual(response.status_code, 200)
        
        # doc_l1 tiene versión aprobada, debe estar en active_documents
        process = next(p for p in response.context["processes"] if p.code == "ESTRAT")
        doc_codes = [d.code for d in process.active_documents]
        self.assertIn("DOC-001", doc_codes)  # Tiene APPROVED
        
        # doc_l3 no tiene versión aprobada (solo DRAFT), no debe estar
        process_l1_misio = next(p for p in response.context["processes"] if p.code == "MISIO")
        process_l2 = process_l1_misio.children.all()[0]
        process_l3 = process_l2.children.all()[0]
        doc_codes_l3 = [d.code for d in process_l3.active_documents]
        self.assertNotIn("DOC-003", doc_codes_l3)  # Sin APPROVED
    
    def test_library_filter_by_process_type(self):
        """Debe permitir filtrar por tipo de proceso."""
        response = self.client.get(
            reverse("docs:docs_library"),
            {"process_type": Process.ProcessType.STRATEGIC}
        )
        self.assertEqual(response.status_code, 200)
        
        processes = response.context["processes"]
        # Solo debe tener STRATEGIC
        self.assertTrue(
            all(p.process_type == Process.ProcessType.STRATEGIC for p in processes)
        )
    
    def test_library_filter_by_doc_type(self):
        """Debe permitir filtrar por tipo de documento."""
        response = self.client.get(
            reverse("docs:docs_library"),
            {"doc_type": Document.DocType.PROCEDURE}
        )
        self.assertEqual(response.status_code, 200)
        
        processes = response.context["processes"]
        # Solo debe mostrar PROCEDURE docs
        for p in processes:
            if p.active_documents:
                self.assertTrue(
                    all(d.doc_type == Document.DocType.PROCEDURE for d in p.active_documents)
                )
    
    def test_library_current_version_attached_to_docs(self):
        """Cada documento debe tener current_version cuando tiene APPROVED."""
        response = self.client.get(reverse("docs:docs_library"))
        self.assertEqual(response.status_code, 200)
        
        process = next(p for p in response.context["processes"] if p.code == "ESTRAT")
        doc = next(d for d in process.active_documents if d.code == "DOC-001")
        
        self.assertIsNotNone(doc.current_version)
        self.assertEqual(doc.current_version.version_number, "1.0")
        self.assertEqual(doc.current_version.status, DocumentVersion.Status.APPROVED)
    
    def test_library_context_data(self):
        """El contexto debe incluir opciones de filtro."""
        response = self.client.get(reverse("docs:docs_library"))
        self.assertEqual(response.status_code, 200)
        
        context = response.context
        self.assertIn("sites", context)
        self.assertIn("process_types", context)
        self.assertIn("doc_types", context)
        self.assertIn("selected_site_id", context)
        self.assertIn("selected_process_type", context)
        self.assertIn("selected_doc_type", context)
    
    def test_library_empty_result(self):
        """Cuando no hay resultados, debe mostrar mensaje."""
        response = self.client.get(
            reverse("docs:docs_library"),
            {
                "process_type": Process.ProcessType.SUPPORT,  # No hay procesos SUPPORT
            }
        )
        self.assertEqual(response.status_code, 200)
        
        processes = response.context["processes"]
        self.assertEqual(len(processes), 0)
    
    def test_library_preserves_tree_structure(self):
        """La estructura jerárquica de procesos debe preservarse."""
        response = self.client.get(reverse("docs:docs_library"))
        self.assertEqual(response.status_code, 200)
        
        # Obtener MISIO (level 1)
        process_l1 = next(
            p for p in response.context["processes"] if p.code == "MISIO"
        )
        
        # Debe tener children (nivel 2)
        self.assertEqual(len(process_l1.children.all()), 1)
        
        # Nivel 2 debe tener children (nivel 3)
        process_l2 = process_l1.children.all()[0]
        self.assertEqual(len(process_l2.children.all()), 1)
        self.assertEqual(process_l2.children.all()[0].code, "MISIO.01.01")

    def test_library_with_hx_request_returns_only_partial(self):
        """HX-Request en biblioteca debe devolver solo bloque parcial."""
        response = self.client.get(
            reverse("docs:docs_library"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "processes-tree")
        self.assertNotContains(response, "<html")

    def test_document_list_with_hx_request_returns_only_partial(self):
        """HX-Request en lista de documentos debe devolver solo resultados."""
        response = self.client.get(
            reverse("docs:docs_list"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "doc-list")
        self.assertNotContains(response, "<html")

    def test_document_list_hx_filter_by_doc_type(self):
        """Filtros HTMX en documentos no rompen queryset."""
        response = self.client.get(
            reverse("docs:docs_list"),
            {"doc_type": Document.DocType.PROCEDURE},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DOC-002")
        self.assertNotContains(response, "DOC-001")
