from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.core.models import NoConformity, NonconformingOutput, Organization, Process, Site

User = get_user_model()


class APITestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org", is_active=True)
        self.site = Site.objects.create(organization=self.org, name="Planta Test")
        self.user = User.objects.create_user(
            username="apiuser",
            password="testpass",
            first_name="API",
            last_name="User",
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.process = Process.objects.create(
            organization=self.org,
            site=self.site,
            code="09",
            name="Producción",
            process_type="MISSIONAL",
            level=1,
        )

    def test_health(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")

    def test_process_list(self):
        active_org = Organization.objects.filter(is_active=True).first()
        active_site = Site.objects.create(organization=active_org, name="Planta API")
        Process.objects.create(
            organization=active_org,
            site=active_site,
            code="10",
            name="Compras",
            process_type="SUPPORT",
            level=1,
        )
        response = self.client.get("/api/processes/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_user_list(self):
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, 200)

    def test_create_nc(self):
        response = self.client.post(
            "/api/nc/create/",
            {
                "title": "Test NC desde API",
                "description": "Creada desde test",
                "origin": "INTERNAL",
                "severity": "MINOR",
                "detected_at": "2026-03-01",
            },
        )
        self.assertEqual(response.status_code, 201)
        nc = NoConformity.objects.get(title="Test NC desde API")
        self.assertTrue(nc.code.startswith("NC-"))

    def test_nc_list(self):
        response = self.client.get("/api/nc/")
        self.assertEqual(response.status_code, 200)

    def test_create_pnc(self):
        response = self.client.post(
            "/api/pnc/create/",
            {
                "product_or_service": "Tolva 26tn",
                "description": "Soldadura fuera de especificación",
                "detected_at": "2026-03-02",
                "severity": "MAJOR",
                "related_process": self.process.id,
                "site": self.site.id,
            },
        )
        self.assertEqual(response.status_code, 201)
        pnc = NonconformingOutput.objects.get(product_or_service="Tolva 26tn")
        self.assertTrue(pnc.code.startswith("PNC-"))

    def test_pnc_list(self):
        active_org = Organization.objects.filter(is_active=True).first()
        active_site = Site.objects.create(organization=active_org, name="Planta API PNC")
        active_process = Process.objects.create(
            organization=active_org,
            site=active_site,
            code="11",
            name="Calidad",
            process_type="SUPPORT",
            level=1,
        )

        pnc = NonconformingOutput.objects.create(
            organization=active_org,
            site=active_site,
            related_process=active_process,
            detected_at="2026-03-03",
            product_or_service="Servicio postventa",
            description="Tiempo de respuesta fuera de SLA",
            severity="MINOR",
        )

        response = self.client.get("/api/pnc/")
        self.assertEqual(response.status_code, 200)

        payload = response.data.get("results", response.data)
        codes = [item["code"] for item in payload]
        self.assertIn(pnc.code, codes)

    def test_create_pnc_with_quantity(self):
        response = self.client.post(
            "/api/pnc/create/",
            {
                "product_or_service": "Lote de tornillos",
                "description": "Cantidad fuera de tolerancia",
                "detected_at": "2026-03-04",
                "severity": "MINOR",
                "quantity": "12.50",
            },
        )
        self.assertEqual(response.status_code, 201)
        pnc = NonconformingOutput.objects.get(product_or_service="Lote de tornillos")
        self.assertEqual(pnc.quantity, Decimal("12.50"))

    def test_create_interaction(self):
        response = self.client.post(
            "/api/interaction/create/",
            {
                "date": "2026-03-10",
                "customer_name": "Gauss Maquinarias",
                "project": "Pala M1001",
                "channel": "WHATSAPP",
                "interaction_type": "CLAIM",
                "topic": "QUALITY",
                "perception": "NEGATIVE",
                "impact": "HIGH",
                "observations": "Reclamo por soldadura defectuosa",
                "source": "TELEGRAM_AUDIO",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["code"].startswith("IC-"))
        self.assertIn("id", response.data)

    def test_interaction_list(self):
        response = self.client.get("/api/interaction/")
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/health/")
        self.assertEqual(response.status_code, 401)
