from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.core.models import NoConformity, Organization, Process, Site

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

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/health/")
        self.assertEqual(response.status_code, 401)
