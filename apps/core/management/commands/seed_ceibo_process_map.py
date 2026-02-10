from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Organization, Site, Process


class Command(BaseCommand):
	help = "Carga datos iniciales del mapa de procesos de Metalurgica Ceibo."

	def handle(self, *args, **options):
		with transaction.atomic():
			organization, _ = Organization.objects.update_or_create(
				name="Metalurgica Ceibo S.R.L.",
				defaults={"is_active": True},
			)
			site, _ = Site.objects.update_or_create(
				organization=organization,
				name="Metalurgica Ceibo",
				defaults={"is_active": True},
			)

			process_type_by_code = {
				"STRATEGIC": {"00", "02", "03", "16"},
				"MISSIONAL": {"07", "09", "10", "11"},
				"SUPPORT": {"01", "04", "05", "06", "08", "12", "13", "14", "15"},
			}

			level1_items = [
				("00", "ANALISIS DEL CONTEXTO DE LA ORGANIZACION", []),
				("01", "INFORMACION DOCUMENTADA", []),
				("02", "PLANIFICACION Y GESTION DEL CAMBIO", []),
				("03", "GESTION DE RIESGOS Y OPORTUNIDADES", []),
				("04", "AUDITORIA", []),
				("05", "NO CONFORMIDADES", []),
				("06", "SEGUIMIENTO Y MEDICION", []),
				("07", "GESTION DE VENTAS/ COMERCIALIZACION", []),
				("08", "GESTION DE COMPRAS", []),
				(
					"09",
					"PLANIFICACION Y EJECUCION DE LA PRODUCCION",
					[
						(
							"01",
							"ELABORACION INICIAL DE MATERIAS PRIMAS",
							[
								("01", "CORTE PANTOGRAFO (C1)"),
								("02", "RECOPILACION DE PIEZAS"),
								("03", "AMOLADO (M2)"),
								("04", "CORTE DE PIEZAS"),
								("05", "AGUJEREADO"),
							],
						),
						(
							"02",
							"SOLDADURA",
							[
								("06", "SOLDADO/ARMADO (S1) PALAS FRONTALES"),
								("07", "SOLDADO/ARMADO (S2) CONJUNTO PALA"),
								("08", "SOLDADO/ARMADO (S3) RETROEXCAVADORAS/VOLCADORES"),
								("09", "SOLDADO/ARMADO (S4) GRUAS DE ARRASTRE / NIVELADORA"),
								("10", "SOLDADO/ARMADO (S5) TANQUE DE COMBUSTIBLES"),
								("11", "SOLDADO/ARMADO (S6) COLOCACION DE PALAS FRONTALES"),
							],
						),
						(
							"03",
							"LIMPIEZA Y PINTURA",
							[
								("12", "LIMPIEZA Y PRE PINTURA"),
								("13", "PINTURA"),
							],
						),
						("04", "ARMADO FINAL", []),
						("05", "CONTROL DIMENSIONAL, LOGISTICA, LIBERACION Y ENTREGA", []),
					],
				),
				("10", "DISENO Y DESARROLLO", []),
				("11", "POST VENTA", []),
				("12", "GESTION DE RRHH / FORMACION", []),
				("13", "GESTION DE LA INFRAESTRUCTURA Y MTTO.", []),
				("14", "COMUNICACION", []),
				("15", "SATISFACCION AL CLIENTE", []),
				("16", "MEJORA CONTINUA MSC-01", []),
			]

			created_count = 0
			updated_count = 0

			def resolve_process_type(code_level1):
				for process_type, codes in process_type_by_code.items():
					if code_level1 in codes:
						return Process.ProcessType[process_type]
				return Process.ProcessType.SUPPORT

			def upsert_process(**kwargs):
				nonlocal created_count, updated_count
				lookup = {
					"organization": kwargs["organization"],
					"code": kwargs["code"],
				}
				defaults = {
					"name": kwargs["name"],
					"process_type": kwargs["process_type"],
					"level": kwargs["level"],
					"parent": kwargs.get("parent"),
					"site": kwargs["site"],
					"is_active": kwargs.get("is_active", True),
				}
				obj, created = Process.objects.update_or_create(
					**lookup,
					defaults=defaults,
				)
				if created:
					created_count += 1
				else:
					updated_count += 1
				return obj

			for code_level1, name_level1, children in level1_items:
				process_type = resolve_process_type(code_level1)
				level1 = upsert_process(
					organization=organization,
					site=site,
					code=code_level1,
					name=name_level1,
					process_type=process_type,
					level=Process.Level.PROCESS,
					parent=None,
					is_active=True,
				)

				for sub_code2, name_level2, sectors in children:
					code_level2 = f"{code_level1}.{sub_code2}"
					level2 = upsert_process(
						organization=organization,
						site=site,
						code=code_level2,
						name=name_level2,
						process_type=process_type,
						level=Process.Level.SUBPROCESS,
						parent=level1,
						is_active=True,
					)

					for sector_code3, name_level3 in sectors:
						code_level3 = f"{code_level1}.{sub_code2}.{sector_code3}"
						upsert_process(
							organization=organization,
							site=site,
							code=code_level3,
							name=name_level3,
							process_type=process_type,
							level=Process.Level.SECTOR,
							parent=level2,
							is_active=True,
						)

		self.stdout.write(
			self.style.SUCCESS(
				f"Process creados: {created_count} | actualizados: {updated_count}"
			)
		)
