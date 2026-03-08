from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.models import (
    CAPAAction,
    NoConformity,
    NonconformingOutput,
    Organization,
    Process,
)

User = get_user_model()


class ProcessListSerializer(serializers.ModelSerializer):
    """Serializer liviano para listar procesos (bot muestra opciones)."""

    class Meta:
        model = Process
        fields = ["id", "code", "name", "process_type", "level"]


class UserListSerializer(serializers.ModelSerializer):
    """Serializer liviano para listar usuarios."""

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class NoConformityCreateSerializer(serializers.ModelSerializer):
    """Serializer para CREAR una NC desde el bot de Telegram."""

    class Meta:
        model = NoConformity
        fields = [
            "title",
            "description",
            "origin",
            "severity",
            "related_process",
            "site",
            "detected_at",
            "detected_by",
            "owner",
            "due_date",
        ]

    def create(self, validated_data):
        org = Organization.objects.filter(is_active=True).first()
        validated_data["organization"] = org
        return super().create(validated_data)


class NoConformityDetailSerializer(serializers.ModelSerializer):
    """Serializer para leer detalle de NC."""

    related_process_name = serializers.CharField(
        source="related_process.name", read_only=True, default=""
    )
    owner_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    origin_display = serializers.CharField(source="get_origin_display", read_only=True)

    class Meta:
        model = NoConformity
        fields = [
            "id",
            "code",
            "title",
            "description",
            "origin",
            "origin_display",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "related_process",
            "related_process_name",
            "detected_at",
            "owner",
            "owner_name",
            "due_date",
            "created_at",
        ]

    def get_owner_name(self, obj):
        if obj.owner:
            name = f"{obj.owner.first_name} {obj.owner.last_name}".strip()
            return name or obj.owner.username
        return ""


class CAPACreateSerializer(serializers.ModelSerializer):
    """Serializer para crear CAPA desde el bot."""

    class Meta:
        model = CAPAAction
        fields = [
            "no_conformity",
            "title",
            "description",
            "action_type",
            "owner",
            "due_date",
        ]

    def create(self, validated_data):
        org = Organization.objects.filter(is_active=True).first()
        validated_data["organization"] = org
        return super().create(validated_data)


class PNCCreateSerializer(serializers.ModelSerializer):
    """Serializer para CREAR un PNC desde el bot de Telegram."""

    code = serializers.CharField(read_only=True)

    class Meta:
        model = NonconformingOutput
        fields = [
            "code",
            "product_or_service",
            "description",
            "detected_at",
            "detected_by",
            "quantity",
            "severity",
            "related_process",
            "site",
            "disposition",
            "disposition_notes",
            "responsible",
        ]

    def create(self, validated_data):
        org = Organization.objects.filter(is_active=True).first()
        validated_data["organization"] = org
        return super().create(validated_data)


class PNCDetailSerializer(serializers.ModelSerializer):
    """Serializer para leer detalle de PNC."""

    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    disposition_display = serializers.CharField(
        source="get_disposition_display", read_only=True, default=""
    )
    related_process_name = serializers.CharField(
        source="related_process.name", read_only=True, default=""
    )
    responsible_name = serializers.SerializerMethodField()

    class Meta:
        model = NonconformingOutput
        fields = [
            "id",
            "code",
            "product_or_service",
            "description",
            "detected_at",
            "quantity",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "disposition",
            "disposition_display",
            "disposition_notes",
            "related_process",
            "related_process_name",
            "responsible",
            "responsible_name",
            "linked_nc",
            "created_at",
        ]

    def get_responsible_name(self, obj):
        if obj.responsible:
            name = f"{obj.responsible.first_name} {obj.responsible.last_name}".strip()
            return name or obj.responsible.username
        return ""
