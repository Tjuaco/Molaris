from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import TrabajadorLoginView
from . import views_proveedores
from . import views_mensajes

urlpatterns = [
    # Auth trabajadores
    path('', views.inicio, name='inicio'),
    path('login/', TrabajadorLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),

    # Panel trabajador
    path('panel/', views.panel_trabajador, name='panel_trabajador'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard-reportes/', views.dashboard_reportes, name='dashboard_reportes'),
    path('exportar-excel-citas/', views.exportar_excel_citas, name='exportar_excel_citas'),
    path('exportar-excel-clientes/', views.exportar_excel_clientes, name='exportar_excel_clientes'),
    path('exportar-excel-insumos/', views.exportar_excel_insumos, name='exportar_excel_insumos'),
    path('exportar-excel-finanzas/', views.exportar_excel_finanzas, name='exportar_excel_finanzas'),
    
    # Gestión de citas (solo administrativos)
    path('agregar_hora/', views.agregar_hora, name='agregar_hora'),
    path('editar_cita/<int:cita_id>/', views.editar_cita, name='editar_cita'),
    path('ajustar_precio_cita/<int:cita_id>/', views.ajustar_precio_cita, name='ajustar_precio_cita'),
    path('todas_las_citas/', views.todas_las_citas, name='todas_las_citas'),
    path('confirmar_cita/<int:cita_id>/', views.confirmar_cita, name='confirmar_cita'),
    path('cancelar_cita/<int:cita_id>/', views.cancelar_cita_admin, name='cancelar_cita_admin'),
    path('completar_cita/<int:cita_id>/', views.completar_cita, name='completar_cita'),
    path('eliminar_cita/<int:cita_id>/', views.eliminar_cita, name='eliminar_cita'),
    path('citas_tomadas/', views.citas_tomadas, name='citas_tomadas'),
    path('citas_completadas/', views.citas_completadas, name='citas_completadas'),
    path('gestor_clientes/', views.gestor_clientes, name='gestor_clientes'),
    
    # Gestión de insumos
    path('gestor_insumos/', views.gestor_insumos, name='gestor_insumos'),
    path('agregar_insumo/', views.agregar_insumo, name='agregar_insumo'),
    path('editar_insumo/<int:insumo_id>/', views.editar_insumo, name='editar_insumo'),
    path('movimiento_insumo/<int:insumo_id>/', views.movimiento_insumo, name='movimiento_insumo'),
    path('historial_movimientos/', views.historial_movimientos, name='historial_movimientos'),
    path('exportar_insumos_pdf/', views.exportar_insumos_pdf, name='exportar_insumos_pdf'),
    
    # Gestión de personal
    path('gestor_personal/', views.gestor_personal, name='gestor_personal'),
    path('agregar_personal/', views.agregar_personal, name='agregar_personal'),
    path('editar_personal/<int:personal_id>/', views.editar_personal, name='editar_personal'),
    path('eliminar_personal/<int:personal_id>/', views.eliminar_personal, name='eliminar_personal'),
    path('calendario_personal/', views.calendario_personal, name='calendario_personal'),
    path('asignar_dentista_cita/<int:cita_id>/', views.asignar_dentista_cita, name='asignar_dentista_cita'),
    path('mi_perfil/', views.mi_perfil, name='mi_perfil'),
    path('mis_citas/', views.mis_citas_dentista, name='mis_citas_dentista'),
    path('tomar_cita/<int:cita_id>/', views.tomar_cita_dentista, name='tomar_cita_dentista'),
    
    # Gestión de perfil
    path('registro_trabajador/', views.registro_trabajador, name='registro_trabajador'),
    path('editar_perfil/', views.editar_perfil, name='editar_perfil'),
    
    # Gestión de pacientes por dentista
    path('gestionar_pacientes/', views.gestionar_pacientes, name='gestionar_pacientes'),
    path('detalle_paciente/<int:paciente_id>/', views.detalle_paciente, name='detalle_paciente'),
    path('agregar_nota_paciente/<int:paciente_id>/', views.agregar_nota_paciente, name='agregar_nota_paciente'),
    path('estadisticas_pacientes/', views.estadisticas_pacientes, name='estadisticas_pacientes'),
    path('asignar_dentista_cliente/<int:cliente_id>/', views.asignar_dentista_cliente, name='asignar_dentista_cliente'),
    
    # Gestión de odontogramas
    path('odontogramas/', views.listar_odontogramas, name='listar_odontogramas'),
    path('odontogramas/crear/', views.crear_odontograma, name='crear_odontograma'),
    path('odontogramas/<int:odontograma_id>/', views.detalle_odontograma, name='detalle_odontograma'),
    path('odontogramas/<int:odontograma_id>/editar/', views.editar_odontograma, name='editar_odontograma'),
    path('odontogramas/<int:odontograma_id>/eliminar/', views.eliminar_odontograma, name='eliminar_odontograma'),
    path('odontogramas/<int:odontograma_id>/diente/<int:numero_diente>/', views.actualizar_diente, name='actualizar_diente'),
    path('odontogramas/<int:odontograma_id>/exportar-pdf/', views.exportar_odontograma_pdf, name='exportar_odontograma_pdf'),
    
    # Gestión de proveedores
    path('proveedores/', views_proveedores.gestor_proveedores, name='gestor_proveedores'),
    path('proveedores/crear/', views_proveedores.crear_proveedor, name='crear_proveedor'),
    path('proveedores/<int:proveedor_id>/editar/', views_proveedores.editar_proveedor, name='editar_proveedor'),
    path('proveedores/<int:proveedor_id>/eliminar/', views_proveedores.eliminar_proveedor, name='eliminar_proveedor'),
    path('proveedores/solicitud/enviar/', views_proveedores.enviar_solicitud_insumo, name='enviar_solicitud_insumo'),
    
    # Gestión de servicios
    path('servicios/', views.gestor_servicios, name='gestor_servicios'),
    path('servicios/crear/', views.crear_servicio, name='crear_servicio'),
    path('servicios/<int:servicio_id>/editar/', views.editar_servicio, name='editar_servicio'),
    path('servicios/<int:servicio_id>/eliminar/', views.eliminar_servicio, name='eliminar_servicio'),
    
    # Gestión de horarios de dentistas
    path('horarios/', views.gestor_horarios, name='gestor_horarios'),
    path('horarios/dentista/<int:dentista_id>/', views.gestionar_horario_dentista, name='gestionar_horario_dentista'),
    path('mi-horario/', views.ver_mi_horario, name='ver_mi_horario'),
    
    # Sistema de mensajería
    path('mensajes/obtener/', views_mensajes.obtener_mensajes, name='obtener_mensajes'),
    path('mensajes/enviar/', views_mensajes.enviar_mensaje, name='enviar_mensaje'),
    path('mensajes/<int:mensaje_id>/marcar-leido/', views_mensajes.marcar_como_leido, name='marcar_como_leido'),
    path('mensajes/<int:mensaje_id>/archivar/', views_mensajes.archivar_mensaje, name='archivar_mensaje'),
    path('mensajes/usuarios-disponibles/', views_mensajes.obtener_usuarios_disponibles, name='obtener_usuarios_disponibles'),
    
    # Gestión de finanzas
    path('finanzas/', views.gestor_finanzas, name='gestor_finanzas'),
    path('finanzas/ingreso/agregar/', views.agregar_ingreso_manual, name='agregar_ingreso_manual'),
    path('finanzas/ingreso/<int:ingreso_id>/eliminar/', views.eliminar_ingreso_manual, name='eliminar_ingreso_manual'),
    path('finanzas/ingreso/cita/<int:cita_id>/eliminar/', views.eliminar_ingreso_cita, name='eliminar_ingreso_cita'),
    path('finanzas/egreso/agregar/', views.agregar_egreso_manual, name='agregar_egreso_manual'),
    path('finanzas/egreso/<int:egreso_id>/eliminar/', views.eliminar_egreso_manual, name='eliminar_egreso_manual'),
    path('finanzas/egreso/compra/<int:movimiento_id>/eliminar/', views.eliminar_egreso_compra, name='eliminar_egreso_compra'),
    path('finanzas/egreso/solicitud/<int:solicitud_id>/eliminar/', views.eliminar_egreso_solicitud, name='eliminar_egreso_solicitud'),
    
    # Información de la clínica
    path('informacion-clinica/obtener/', views.obtener_informacion_clinica, name='obtener_informacion_clinica'),
    path('informacion-clinica/editar/', views.editar_informacion_clinica, name='editar_informacion_clinica'),
    
    # Gestión de clientes
    path('clientes/validar-username/', views.validar_username, name='validar_username'),
    path('clientes/crear/', views.crear_cliente_presencial, name='crear_cliente_presencial'),
    path('clientes/<int:cliente_id>/', views.perfil_cliente, name='perfil_cliente'),
    path('clientes/<int:cliente_id>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:cliente_id>/obtener/', views.obtener_cliente, name='obtener_cliente'),
    path('clientes/<int:cliente_id>/citas/', views.obtener_citas_cliente, name='obtener_citas_cliente'),
    path('clientes/<int:cliente_id>/toggle-estado/', views.toggle_estado_cliente, name='toggle_estado_cliente'),
    path('clientes/<int:cliente_id>/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),
    
    # Gestión de radiografías
    path('radiografias/', views.radiografias_listar, name='radiografias_listar'),
    path('radiografias/paciente/<int:paciente_id>/', views.radiografias_paciente, name='radiografias_paciente'),
    path('radiografias/paciente/<int:paciente_id>/agregar/', views.agregar_radiografia, name='agregar_radiografia'),
    path('radiografias/<int:radiografia_id>/editar/', views.editar_radiografia, name='editar_radiografia'),
    path('radiografias/<int:radiografia_id>/eliminar/', views.eliminar_radiografia, name='eliminar_radiografia'),
    path('radiografias/<int:radiografia_id>/enviar-correo/', views.enviar_radiografia_por_correo, name='enviar_radiografia_por_correo'),
    path('radiografias/<int:radiografia_id>/guardar-anotaciones/', views.guardar_anotaciones_radiografia, name='guardar_anotaciones_radiografia'),
    path('radiografias/<int:radiografia_id>/anotaciones/', views.obtener_anotaciones_radiografia, name='obtener_anotaciones_radiografia'),
]
