"""
Servicios de IA para el sistema ISO 9001.
Usa OpenAI GPT para generar análisis automáticos.
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def generate_satisfaction_analysis(report):
    """
    Genera análisis de satisfacción usando OpenAI GPT.
    Recibe un SatisfactionReport con métricas ya calculadas.
    Devuelve dict con textos generados para cada sección.
    """
    try:
        import openai
    except ImportError:
        logger.error("openai package not installed")
        return None

    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        logger.error("OPENAI_API_KEY not configured")
        return None

    try:
        client = openai.OpenAI(api_key=api_key)
    except Exception as error:
        logger.error(f"Error initializing OpenAI client: {error}")
        return None

    data_context = f"""
Período evaluado: {report.period_label}
Desde: {report.period_start} hasta: {report.period_end}

RESUMEN CUANTITATIVO:
Total de interacciones: {report.total_interactions}

Por tipo:
- Consultas: {report.count_query}
- Reclamos: {report.count_claim}
- Sugerencias: {report.count_suggestion}
- Felicitaciones: {report.count_compliment}
- Postventa: {report.count_after_sales}
- Menciones: {report.count_mention}

Percepción del cliente:
- Positiva: {report.count_positive}
- Neutra: {report.count_neutral}
- Negativa: {report.count_negative}

Impacto:
- Alto: {report.count_high_impact}
- Medio: {report.count_medium_impact}
- Bajo: {report.count_low_impact}

Canal:
- WhatsApp: {report.count_whatsapp}
- Mail: {report.count_mail}
- Teléfono: {report.count_phone}
- Presencial: {report.count_in_person}
- Redes Sociales: {report.count_social}

INDICADORES:
- Índice global de satisfacción: {report.satisfaction_index}%
- % de reclamos sobre total: {report.claim_percentage}%
- Tiempo promedio de resolución de reclamos: {report.avg_resolution_days} días
"""

    from apps.core.models import CustomerInteraction

    interactions = CustomerInteraction.objects.filter(
        organization=report.organization,
        date__gte=report.period_start,
        date__lte=report.period_end,
        is_active=True,
    ).order_by("date")[:50]

    details = ""
    for item in interactions:
        customer = item.get_customer_display()
        observation = item.observations[:100] if item.observations else ""
        details += (
            f"- {item.date}: {customer} | {item.get_interaction_type_display()} | "
            f"{item.get_channel_display()} | {item.get_perception_display()} | {observation}\n"
        )

    prompt = f"""Sos analista de calidad de Metalúrgica Ceibo S.R.L., una fábrica de implementos agrícolas en Armstrong, Santa Fe, Argentina. Tu tarea es generar el análisis de satisfacción del cliente para el informe R-15-02 del Sistema de Gestión de Calidad ISO 9001:2015.

DATOS DEL PERÍODO:
{data_context}

DETALLE DE INTERACCIONES:
{details}

REGLAS ESTRICTAS DE FORMATO:
- Todos los valores DEBEN ser strings de texto plano en español
- PROHIBIDO usar arrays/listas JSON (nunca [])
- PROHIBIDO usar comillas simples dentro de los valores
- Si hay varios puntos, escribirlos como texto corrido separado por saltos de línea: "- Punto uno.\n- Punto dos.\n- Punto tres."
- Ejemplo CORRECTO: "observed_trends": "- La mayoría de las interacciones provienen de redes sociales.\n- Las felicitaciones superan a los reclamos.\n- El canal más utilizado es Instagram."
- Ejemplo INCORRECTO: "observed_trends": ["punto 1", "punto 2"]

Generá un JSON con las siguientes claves (todos los valores son strings con texto en español):

{{
  "general_status": "Estado general de la satisfacción del cliente. 2-3 oraciones.",
  "trend_vs_previous": "Tendencia con respecto al período anterior. Si no hay datos previos, indicar que es el primer período evaluado. 2-3 oraciones.",
  "general_situation": "Situación general: satisfactoria / a mejorar / crítica. Con comentarios de 2-3 oraciones justificando.",
  "observed_trends": "Tendencias observadas en los datos. 3-5 puntos concretos.",
  "comparison_previous": "Comparación con períodos anteriores. Si es el primero, indicar que se establece como línea base.",
  "deviations": "Identificación de desvíos respecto a lo esperado. 2-4 puntos.",
  "improvement_opportunities": "Oportunidades de mejora identificadas. 3-5 puntos accionables y concretos.",
  "satisfaction_result": "ADEQUATE o PARTIALLY o NOT_ADEQUATE",
  "justification": "Justificación breve del resultado. 2-3 oraciones.",
  "action_required": "NONE o PREVENTIVE o CORRECTIVE",
  "actions_description": "Descripción de acciones requeridas. Si no se requieren, dejar vacío."
}}

Respondé SOLAMENTE con el JSON, sin markdown, sin texto adicional.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Sos un analista de calidad ISO 9001. Respondé solo con JSON válido.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        content = response.choices[0].message.content or ""
        clean = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
         # Limpiar valores que vengan como lista en vez de string
        for key, value in result.items():
            if isinstance(value, list):
                result[key] = "\n".join(f"- {item}" for item in value)
        return result

    except Exception as error:
        logger.error(f"Error generating AI analysis: {error}")
        return None
