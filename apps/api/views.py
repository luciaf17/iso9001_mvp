from django.contrib.auth import get_user_model
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import (
    CAPAAction,
    NoConformity,
    NonconformingOutput,
    Organization,
    Process,
)
from apps.core.services import log_audit_event

from .serializers import (
    CAPACreateSerializer,
    NoConformityCreateSerializer,
    NoConformityDetailSerializer,
    PNCCreateSerializer,
    PNCDetailSerializer,
    ProcessListSerializer,
    UserListSerializer,
)

User = get_user_model()


class ProcessListView(generics.ListAPIView):
    """GET /api/processes/ — Lista procesos para que el bot muestre opciones."""

    serializer_class = ProcessListSerializer

    def get_queryset(self):
        org = Organization.objects.filter(is_active=True).first()
        queryset = Process.objects.filter(organization=org, is_active=True)
        level = self.request.query_params.get("level")
        if level:
            queryset = queryset.filter(level=level)
        return queryset.order_by("code")


class UserListView(generics.ListAPIView):
    """GET /api/users/ — Lista usuarios para asignar responsables."""

    serializer_class = UserListSerializer

    def get_queryset(self):
        return User.objects.filter(is_active=True).order_by("first_name")


class NCCreateView(generics.CreateAPIView):
    """POST /api/nc/create/ — Crear NC desde bot de Telegram."""

    serializer_class = NoConformityCreateSerializer

    def perform_create(self, serializer):
        nc = serializer.save()
        log_audit_event(
            actor=self.request.user,
            action="core.nc.created",
            instance=nc,
            metadata={"source": "telegram_bot", "code": nc.code},
        )


class NCDetailView(generics.RetrieveAPIView):
    """GET /api/nc/<id>/ — Ver detalle de NC (para confirmación del bot)."""

    serializer_class = NoConformityDetailSerializer

    def get_queryset(self):
        org = Organization.objects.filter(is_active=True).first()
        return NoConformity.objects.filter(organization=org)


class NCListView(generics.ListAPIView):
    """GET /api/nc/ — Listar NCs (filtros: status, severity)."""

    serializer_class = NoConformityDetailSerializer

    def get_queryset(self):
        org = Organization.objects.filter(is_active=True).first()
        queryset = NoConformity.objects.filter(organization=org, is_active=True)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        severity = self.request.query_params.get("severity")
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset.order_by("-created_at")


class CAPACreateView(generics.CreateAPIView):
    """POST /api/capa/create/ — Crear acción CAPA desde bot."""

    serializer_class = CAPACreateSerializer

    def perform_create(self, serializer):
        capa = serializer.save()
        log_audit_event(
            actor=self.request.user,
            action="core.capa_action.created",
            instance=capa,
            metadata={"source": "telegram_bot"},
        )


class PNCCreateView(generics.CreateAPIView):
    """POST /api/pnc/create/ — Crear PNC desde bot de Telegram."""

    serializer_class = PNCCreateSerializer

    def perform_create(self, serializer):
        pnc = serializer.save()
        log_audit_event(
            actor=self.request.user,
            action="core.pnc.created",
            instance=pnc,
            metadata={"source": "telegram_bot", "code": pnc.code},
        )


class PNCDetailView(generics.RetrieveAPIView):
    """GET /api/pnc/<id>/ — Ver detalle de PNC."""

    serializer_class = PNCDetailSerializer

    def get_queryset(self):
        org = Organization.objects.filter(is_active=True).first()
        return NonconformingOutput.objects.filter(organization=org)


class PNCListView(generics.ListAPIView):
    """GET /api/pnc/ — Listar PNCs."""

    serializer_class = PNCDetailSerializer

    def get_queryset(self):
        org = Organization.objects.filter(is_active=True).first()
        queryset = NonconformingOutput.objects.filter(organization=org, is_active=True)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        severity = self.request.query_params.get("severity")
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset.order_by("-detected_at")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_health(request):
    """GET /api/health/ — Health check para n8n."""

    org = Organization.objects.filter(is_active=True).first()
    return Response(
        {
            "status": "ok",
            "organization": org.name if org else None,
        }
    )
