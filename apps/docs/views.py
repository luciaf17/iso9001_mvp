from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse

from apps.core.models import Process
from apps.core.services import log_audit_event
from .models import Document, DocumentVersion
from .forms import DocumentForm, DocumentVersionForm
from .services import approve_document_version, user_can_approve


def user_in_groups(user, group_names):
    """Verifica si el usuario pertenece a alguno de los grupos especificados."""
    return user.groups.filter(name__in=group_names).exists()


def can_create_document(user):
    """Verifica si el usuario puede crear documentos."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user_in_groups(user, ["Admin", "Calidad", "Responsable"])


def can_upload_version(user):
    """Verifica si el usuario puede subir versiones de documentos."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user_in_groups(user, ["Admin", "Calidad", "Responsable"])


def get_current_version(document):
    """Obtiene la última versión aprobada de un documento."""
    return document.versions.filter(status=DocumentVersion.Status.APPROVED).order_by('-created_at').first()


@login_required
def document_list(request):
    """Lista de documentos filtrable."""
    documents = Document.objects.filter(is_active=True).select_related('owner').prefetch_related('processes').order_by('code')
    
    # Aplicar filtros GET
    doc_type = request.GET.get('doc_type')
    process_id = request.GET.get('process_id')
    
    if doc_type:
        documents = documents.filter(doc_type=doc_type)
    if process_id:
        documents = documents.filter(processes__id=process_id).distinct()
    
    # Agregar versión vigente a cada documento
    for doc in documents:
        doc.current_version = get_current_version(doc)
    
    context = {
        'documents': documents,
        'doc_types': Document.DocType.choices,
        'processes': Process.objects.filter(is_active=True).order_by('code'),
        'can_create': can_create_document(request.user),
        'selected_doc_type': doc_type,
        'selected_process_id': process_id,
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, 'docs/partials/document_list_results.html', context)

    return render(request, 'docs/document_list.html', context)


@login_required
def document_create(request):
    """Crear nuevo documento."""
    if not can_create_document(request.user):
        messages.error(request, 'No tienes permisos para crear documentos.')
        return redirect('docs:docs_list')
    
    if request.method == 'POST':
        form = DocumentForm(request.POST)
        if form.is_valid():
            document = form.save()
            log_audit_event(
                actor=request.user,
                action="docs.document.created",
                instance=document,
                metadata={
                    "process_ids": list(document.processes.values_list("id", flat=True)),
                },
            )
            messages.success(request, f'Documento {document.code} creado exitosamente.')
            return redirect('docs:docs_detail', pk=document.pk)
    else:
        form = DocumentForm()
    
    return render(request, 'docs/document_form.html', {'form': form})


@login_required
def document_detail(request, pk):
    """Detalle de un documento con sus versiones."""
    document = get_object_or_404(Document.objects.select_related('owner').prefetch_related('processes'), pk=pk)
    versions = document.versions.all().select_related('created_by', 'approval').order_by('-created_at')
    current_version = get_current_version(document)
    can_edit = (
        request.user.is_superuser
        or request.user == document.owner
        or user_in_groups(request.user, ["Admin", "Calidad", "Responsable"])
    )
    
    context = {
        'document': document,
        'versions': versions,
        'current_version': current_version,
        'can_approve': user_can_approve(request.user),
        'can_edit': can_edit,
    }
    return render(request, 'docs/document_detail.html', context)


@login_required
def document_edit(request, pk):
    """Editar un documento existente."""
    document = get_object_or_404(Document, pk=pk)
    can_edit = (
        request.user.is_superuser
        or request.user == document.owner
        or user_in_groups(request.user, ["Admin", "Calidad", "Responsable"])
    )
    if not can_edit:
        messages.error(request, 'No tienes permisos para editar este documento.')
        return redirect('docs:docs_detail', pk=document.pk)

    if request.method == 'POST':
        form = DocumentForm(request.POST, instance=document)
        if form.is_valid():
            document = form.save()
            log_audit_event(
                actor=request.user,
                action="docs.document.updated",
                instance=document,
                metadata={
                    "process_ids": list(document.processes.values_list("id", flat=True)),
                },
            )
            messages.success(request, 'Documento actualizado correctamente')
            return redirect('docs:docs_detail', pk=document.pk)
    else:
        form = DocumentForm(instance=document)

    return render(request, 'docs/document_form.html', {
        'form': form,
        'document': document,
    })


@login_required
def version_create(request, pk):
    """Crear nueva versión de un documento."""
    document = get_object_or_404(Document, pk=pk)
    
    # Verificar permisos
    if not can_upload_version(request.user):
        messages.error(request, 'No tenés permisos para subir versiones.')
        return redirect('docs:docs_detail', pk=document.pk)
    
    if request.method == 'POST':
        form = DocumentVersionForm(
            request.POST,
            request.FILES,
            document=document,
            created_by=request.user
        )
        if form.is_valid():
            version = form.save()
            messages.success(request, f'Versión {version.version_number} creada exitosamente.')
            return redirect('docs:docs_detail', pk=document.pk)
    else:
        form = DocumentVersionForm(document=document, created_by=request.user)
    
    return render(request, 'docs/version_form.html', {
        'form': form,
        'document': document,
    })


@login_required
@require_http_methods(["POST"])
def version_approve(request, version_id):
    """Aprobar una versión de documento.
    
    Solo POST. Requiere login y permisos de aprobación.
    Si es HTMX: devuelve partial actualizado.
    Si no es HTMX: redirige a document_detail.
    """
    # Verificar permisos
    if not user_can_approve(request.user):
        messages.error(request, 'No tienes permisos para aprobar versiones.')
        is_htmx = request.headers.get('HX-Request') == 'true'
        if is_htmx:
            return HttpResponse('Acceso denegado', status=403)
        return redirect('docs:docs_list')
    
    # Obtener versión
    try:
        version = DocumentVersion.objects.select_related('document').get(pk=version_id)
    except DocumentVersion.DoesNotExist:
        if request.headers.get('HX-Request') == 'true':
            return HttpResponse('Versión no encontrada', status=404)
        raise
    
    # Obtener comentario
    comment = request.POST.get('comment', '')
    
    # Llamar servicio de aprobación
    try:
        approve_document_version(
            version_id=version.pk,
            user=request.user,
            comment=comment
        )
        messages.success(request, f'Versión {version.version_number} aprobada exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al aprobar: {str(e)}')
    
    # Responder según tipo de request
    is_htmx = request.headers.get('HX-Request') == 'true'
    if is_htmx:
        # Devolver partial actualizado
        versions = version.document.versions.all().select_related('created_by', 'approval').order_by('-created_at')
        return render(request, 'docs/partials/version_list.html', {
            'document': version.document,
            'versions': versions,
            'can_approve': user_can_approve(request.user),
        })
    
    # Si no es HTMX, redirect
    return redirect('docs:docs_detail', pk=version.document.pk)


@login_required
def docs_library(request):
    """Vista de biblioteca de documentos agrupados por procesos.
    
    Muestra procesos nivel 1 con su árbol de hijos (nivel 2 y 3),
    y bajo cada proceso, los documentos con versión vigente (APPROVED).
    Permite filtrar por:
    - site_id: solo documentos en esa sede
    - process_type: solo procesos de ese tipo  
    - doc_type: solo documentos de ese tipo
    """
    from django.db.models import Q, Exists, OuterRef, Prefetch
    
    # Filtros del usuario
    site_id = request.GET.get('site_id')
    process_type = request.GET.get('process_type')
    doc_type = request.GET.get('doc_type')
    
    # Query base: procesos nivel 1 (top-level)
    processes_l1 = Process.objects.filter(
        level=Process.Level.PROCESS,
        is_active=True
    )
    
    # Aplicar filtro de site
    if site_id:
        processes_l1 = processes_l1.filter(site_id=site_id)
    
    # Aplicar filtro de process_type
    if process_type:
        processes_l1 = processes_l1.filter(process_type=process_type)
    
    # Prefetch children (nivel 2 y 3) con documentos vigentes
    # Para optimizar: traemos todos los hijos y sus documentos
    processes_l1 = processes_l1.prefetch_related(
        'children',
        'children__children',
        'documents',
        'children__documents',
        'children__children__documents'
    ).order_by('code')
    
    # Anotar documentos vigentes por proceso
    # Un documento es "vigente" si tiene al menos una versión APPROVED
    def add_current_versions(process_list):
        """Agrega versión vigente a documentos en árbol.
        
        Solo incluye documentos que tienen al menos una versión APPROVED.
        """
        for process in process_list:
            # Filtrar documentos si se especifica doc_type
            docs = process.documents.filter(is_active=True)
            if doc_type:
                docs = docs.filter(doc_type=doc_type)
            
            # Solo incluir documentos con versión vigente (APPROVED)
            process.active_documents = []
            for doc in docs:
                current_version = get_current_version(doc)
                if current_version:  # Solo si tiene versión APPROVED
                    doc.current_version = current_version
                    process.active_documents.append(doc)
            
            # Recursivamente para hijos
            if hasattr(process, 'children') and process.children.exists():
                add_current_versions(process.children.all())
    
    add_current_versions(processes_l1)
    
    # Obtener opciones para filtros (sin duplicados)
    from apps.core.models import Site
    sites = Site.objects.filter(
        processes__is_active=True
    ).distinct().values_list('id', 'name').order_by('name')
    
    context = {
        'processes': processes_l1,
        'sites': sites,
        'process_types': Process.ProcessType.choices,
        'doc_types': Document.DocType.choices,
        'selected_site_id': site_id,
        'selected_process_type': process_type,
        'selected_doc_type': doc_type,
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, 'docs/partials/docs_library_results.html', context)

    return render(request, 'docs/docs_library.html', context)
