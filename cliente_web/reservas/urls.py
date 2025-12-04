from django.urls import path
from . import views

urlpatterns = [
    path('panel/', views.panel_cliente, name="panel_cliente"),
    path('reservar/<int:cita_id>/', views.reservar_cita, name="reservar_cita"),
    # Enlaces públicos de confirmación
    path('confirmar/<int:cita_id>/', views.confirmar_cita, name="confirmar_cita"),
    path('citas-fecha/', views.obtener_citas_fecha, name="obtener_citas_fecha"),
    
    # URLs del Menú Lateral
    path('mi-perfil/', views.mi_perfil, name="mi_perfil"),
    path('mis-citas-activas/', views.mis_citas_activas, name="mis_citas_activas"),
    path('historial/', views.historial_citas, name="historial_citas"),
    path('ayuda/', views.ayuda, name="ayuda"),
    
    # URLs de Documentos (Fichas y Radiografías)
    path('odontogramas/', views.ver_odontogramas, name="ver_odontogramas"),
    path('odontograma/<int:odontograma_id>/', views.ver_odontograma, name="ver_odontograma"),
    path('odontograma/<int:odontograma_id>/pdf/', views.ver_pdf_odontograma, name="ver_pdf_odontograma"),
    path('odontograma/<int:odontograma_id>/descargar/', views.descargar_odontograma, name="descargar_odontograma"),
    path('radiografias/', views.ver_radiografias, name="ver_radiografias"),
    path('radiografia/<int:radiografia_id>/descargar/', views.descargar_radiografia, name="descargar_radiografia"),
    path('radiografia/<int:radiografia_id>/imagen/', views.ver_imagen_radiografia, name="ver_imagen_radiografia"),
    
    # URLs de Consentimientos Informados
    path('consentimientos/', views.ver_consentimientos, name="ver_consentimientos"),
    path('consentimientos/<int:consentimiento_id>/', views.ver_consentimiento, name="ver_consentimiento"),
    path('consentimientos/<int:consentimiento_id>/firmar/', views.firmar_consentimiento_cliente, name="firmar_consentimiento_cliente"),
    
    # URLs de Presupuestos
    path('presupuestos/', views.ver_presupuestos, name="ver_presupuestos"),
    path('presupuestos/<int:presupuesto_id>/', views.ver_presupuesto, name="ver_presupuesto"),
    path('presupuestos/<int:presupuesto_id>/aceptar/', views.aceptar_presupuesto_cliente, name="aceptar_presupuesto_cliente"),
    
    # URLs de Tratamientos (solo activos con presupuesto aceptado)
    path('tratamientos/', views.ver_tratamientos, name="ver_tratamientos"),
    path('tratamientos/<int:tratamiento_id>/', views.ver_tratamiento, name="ver_tratamiento"),
]
