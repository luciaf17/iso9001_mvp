#!/usr/bin/env python
"""Script para verificar permisos y crear competencias de prueba."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User, Group
from apps.core.models import Organization, Competency, Employee

# Obtener usuario actual (el primero superuser o admin)
users = User.objects.all()
print("=== USUARIOS EN BASE DE DATOS ===")
for user in users[:5]:
    print(f"- {user.username} (superuser={user.is_superuser}, staff={user.is_staff})")
    groups = user.groups.all()
    if groups:
        print(f"  Grupos: {', '.join([g.name for g in groups])}")
    else:
        print(f"  Grupos: (ninguno)")

# Obtener organización activa
print("\n=== ORGANIZACIÓN ACTIVA ===")
org = Organization.objects.filter(is_active=True).first()
if org:
    print(f"Organización: {org.name} (ID={org.id})")
else:
    print("Sin organización activa")

# Crear competencias de prueba si no existen
if org:
    print("\n=== CREANDO COMPETENCIAS DE PRUEBA ===")
    competencies_to_create = [
        {
            "name": "Lectura de planos",
            "description": "Capacidad de interpretar y entender planos técnicos",
            "required_for_position": "Operario de producción"
        },
        {
            "name": "Soldadura MIG",
            "description": "Dominio de técnicas de soldadura MIG/MAG",
            "required_for_position": "Soldador"
        },
        {
            "name": "Control de calidad",
            "description": "Inspección visual y dimensional de productos",
            "required_for_position": "Inspector de calidad"
        },
        {
            "name": "Seguridad e higiene",
            "description": "Conocimiento de normas de seguridad ocupacional",
            "required_for_position": "Todos"
        },
    ]
    
    for comp_data in competencies_to_create:
        comp, created = Competency.objects.get_or_create(
            organization=org,
            name=comp_data["name"],
            defaults={
                "description": comp_data["description"],
                "required_for_position": comp_data["required_for_position"],
            }
        )
        status = "✓ CREADA" if created else "✓ YA EXISTE"
        print(f"{status}: {comp.name}")

    print("\n=== COMPETENCIAS EN BASE DE DATOS ===")
    competencies = Competency.objects.filter(organization=org)
    for comp in competencies:
        print(f"- {comp.name} (para: {comp.required_for_position})")

    print("\n=== EMPLEADOS EN BASE DE DATOS ===")
    employees = Employee.objects.filter(organization=org)
    if employees.exists():
        for emp in employees[:5]:
            print(f"- {emp.first_name} {emp.last_name} ({emp.position})")
    else:
        print("Sin empleados registrados")

print("\n✓ CONFIGURACIÓN COMPLETADA")
