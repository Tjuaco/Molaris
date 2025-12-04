from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import TrabajadorLoginView
from . import views_proveedores
from . import views_mensajes
from . import views_inventario
from . import views_dashboard
from . import views_reportes
from . import views_auditoria

urlpatterns = [
    # Auth trabajadores
    path('', views.inicio, name='inicio'),
    path('login/', TrabajadorLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),

    # Panel trabajador
    path('panel/', views.panel_trabajador, name='panel_trabajador'),
    path('panel/citas-dia-ajax/', views.obtener_citas_dia_ajax, name='obtener_citas_dia_ajax'),
    path('obtener_cita/<int:cita_id>/', views.obtener_cita, name='obtener_cita'),
    
    # Gestión de citas con navbar lateral
    path('citas/dia/', views.citas_dia, name='citas_dia'),
    path('citas/disponibles/', views.citas_disponibles, name='citas_disponibles'),
    path('citas/tomadas/', views.citas_tomadas, name='citas_tomadas'),
    path('citas/completadas/', views.citas_completadas, name='citas_completadas'),
    path('citas/calendario/', views.calendario_citas, name='calendario_citas'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard-dentista/', views.dashboard_dentista, name='dashboard_dentista'),
    path('dashboard-reportes/', views_dashboard.dashboard_reportes, name='dashboard_reportes'),
    path('reportes/', views_reportes.reportes, name='reportes'),
    path('estadisticas/', views_reportes.estadisticas, name='estadisticas'),
    path('exportar-excel-citas/', views_reportes.exportar_excel_citas, name='exportar_excel_citas'),
    path('exportar-excel-clientes/', views_reportes.exportar_excel_clientes, name='exportar_excel_clientes'),
    path('exportar-excel-insumos/', views_reportes.exportar_excel_insumos, name='exportar_excel_insumos'),
    path('exportar-excel-finanzas/', views_reportes.exportar_excel_finanzas, name='exportar_excel_finanzas'),
    path('exportar-excel-proveedores/', views_reportes.exportar_excel_proveedores, name='exportar_excel_proveedores'),
    path('exportar-excel-solicitudes/', views_reportes.exportar_excel_solicitudes, name='exportar_excel_solicitudes'),
    path('exportar-excel-personal/', views_reportes.exportar_excel_personal, name='exportar_excel_personal'),
    path('exportar-excel-servicios/', views_reportes.exportar_excel_servicios, name='exportar_excel_servicios'),
    path('exportar-excel-planes-tratamiento/', views_reportes.exportar_excel_planes_tratamiento, name='exportar_excel_planes_tratamiento'),
    
    # Gestión de citas (solo administrativos)
    path('agregar_hora/', views.agregar_hora, name='agregar_hora'),
    path('editar_cita/<int:cita_id>/', views.editar_cita, name='editar_cita'),
    path('ajustar_precio_cita/<int:cita_id>/', views.ajustar_precio_cita, name='ajustar_precio_cita'),
    path('todas_las_citas/', views.todas_las_citas, name='todas_las_citas'),
    path('marcar_llegada/<int:cita_id>/', views.marcar_llegada, name='marcar_llegada'),
    path('marcar_listo_para_atender/<int:cita_id>/', views.marcar_listo_para_atender, name='marcar_listo_para_atender'),
    path('iniciar_atencion/<int:cita_id>/', views.iniciar_atencion, name='iniciar_atencion'),
    path('finalizar_atencion/<int:cita_id>/', views.finalizar_atencion, name='finalizar_atencion'),
    path('completar_cita_recepcion/<int:cita_id>/', views.completar_cita_recepcion, name='completar_cita_recepcion'),
    path('marcar_no_llego/<int:cita_id>/', views.marcar_no_llego, name='marcar_no_llego'),
    path('marcar_no_show/<int:cita_id>/', views.marcar_no_show, name='marcar_no_show'),
    path('reagendar_cita/<int:cita_id>/', views.reagendar_cita, name='reagendar_cita'),
    path('confirmar_cita/<int:cita_id>/', views.confirmar_cita, name='confirmar_cita'),
    path('cancelar_cita/<int:cita_id>/', views.cancelar_cita_admin, name='cancelar_cita_admin'),
    path('completar_cita/<int:cita_id>/', views.completar_cita, name='completar_cita'),
    path('eliminar_cita/<int:cita_id>/', views.eliminar_cita, name='eliminar_cita'),
    path('gestor_clientes/', views.gestor_clientes, name='gestor_clientes'),
    
    # Gestión de insumos
    path('gestor_insumos/', views.gestor_insumos, name='gestor_insumos'),
    path('inventario/', views_inventario.gestor_inventario_unificado, name='gestor_inventario_unificado'),
    path('agregar_insumo/', views.agregar_insumo, name='agregar_insumo'),
    path('editar_insumo/<int:insumo_id>/', views.editar_insumo, name='editar_insumo'),
    path('eliminar_insumo/<int:insumo_id>/', views.eliminar_insumo, name='eliminar_insumo'),
    path('movimiento_insumo/<int:insumo_id>/', views.movimiento_insumo, name='movimiento_insumo'),
    path('historial_movimientos/', views.historial_movimientos, name='historial_movimientos'),
    path('exportar_insumos_pdf/', views.exportar_insumos_pdf, name='exportar_insumos_pdf'),
    
    # Gestión de personal
    path('gestor_personal/', views.gestor_personal, name='gestor_personal'),
    path('agregar_personal/', views.agregar_personal, name='agregar_personal'),
    path('editar_personal/<int:personal_id>/', views.editar_personal, name='editar_personal'),
    path('eliminar_personal/<int:personal_id>/', views.eliminar_personal, name='eliminar_personal'),
    path('personal/<int:personal_id>/toggle-estado/', views.toggle_estado_personal, name='toggle_estado_personal'),
    path('calendario_personal/', views.calendario_personal, name='calendario_personal'),
    path('asignar_dentista_cita/<int:cita_id>/', views.asignar_dentista_cita, name='asignar_dentista_cita'),
    path('mi_perfil/', views.mi_perfil, name='mi_perfil'),
    path('obtener_perfil_json/', views.obtener_perfil_json, name='obtener_perfil_json'),
    path('mis_citas/', views.mis_citas_dentista, name='mis_citas_dentista'),
    path('tomar_cita/<int:cita_id>/', views.tomar_cita_dentista, name='tomar_cita_dentista'),
    
    # Gestión de perfil
    path('registro_trabajador/', views.registro_trabajador, name='registro_trabajador'),
    path('editar_perfil/', views.editar_perfil, name='editar_perfil'),
    
    # Gestión de pacientes por dentista
    path('gestionar_pacientes/', views.gestionar_pacientes, name='gestionar_pacientes'),
    path('estadisticas_paciente_json/<int:paciente_id>/', views.estadisticas_paciente_json, name='estadisticas_paciente_json'),
    path('estadisticas_pacientes/', views.estadisticas_pacientes, name='estadisticas_pacientes'),
    path('asignar_dentista_cliente/<int:cliente_id>/', views.asignar_dentista_cliente, name='asignar_dentista_cliente'),
    
    # Mis Pacientes (Vista unificada para dentistas)
    path('mis-pacientes/', views.mis_pacientes, name='mis_pacientes'),
    path('mis-pacientes/<int:paciente_id>/', views.mis_pacientes, name='mis_pacientes_paciente'),
    path('mis-pacientes/<int:paciente_id>/<str:seccion>/', views.mis_pacientes, name='mis_pacientes_seccion'),
    
    # Gestión de odontogramas
    path('odontogramas/', views.listar_odontogramas, name='listar_odontogramas'),
    path('odontogramas/crear/', views.crear_odontograma, name='crear_odontograma'),
    path('odontogramas/<int:odontograma_id>/', views.detalle_odontograma, name='detalle_odontograma'),
    path('odontogramas/<int:odontograma_id>/editar/', views.editar_odontograma, name='editar_odontograma'),
    path('odontogramas/<int:odontograma_id>/eliminar/', views.eliminar_odontograma, name='eliminar_odontograma'),
    path('odontogramas/<int:odontograma_id>/diente/<int:numero_diente>/', views.actualizar_diente, name='actualizar_diente'),
    path('odontogramas/<int:odontograma_id>/exportar-pdf/', views.exportar_odontograma_pdf, name='exportar_odontograma_pdf'),
    
    # Gestión de Planes de Tratamiento
    path('planes-tratamiento/', views.listar_planes_tratamiento, name='listar_planes_tratamiento'),
    path('planes-tratamiento/crear/', views.crear_plan_tratamiento, name='crear_plan_tratamiento'),
    path('planes-tratamiento/crear-desde-odontograma/<int:odontograma_id>/', views.crear_plan_desde_odontograma, name='crear_plan_desde_odontograma'),
    path('planes-tratamiento/<int:plan_id>/', views.detalle_plan_tratamiento, name='detalle_plan_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/editar/', views.editar_plan_tratamiento, name='editar_plan_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/eliminar/', views.eliminar_plan_tratamiento, name='eliminar_plan_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/aceptar-presupuesto/', views.aceptar_presupuesto_tratamiento, name='aceptar_presupuesto_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/aprobar/', views.aprobar_tratamiento, name='aprobar_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/finalizar/', views.finalizar_tratamiento, name='finalizar_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/cancelar/', views.cancelar_plan_tratamiento, name='cancelar_plan_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/crear-cita/', views.crear_cita_desde_plan, name='crear_cita_desde_plan'),
    # Gestión de Fases de Tratamiento
    path('planes-tratamiento/<int:plan_id>/fases/agregar/', views.agregar_fase_tratamiento, name='agregar_fase_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/fases/<int:fase_id>/editar/', views.editar_fase_tratamiento, name='editar_fase_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/fases/<int:fase_id>/eliminar/', views.eliminar_fase_tratamiento, name='eliminar_fase_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/fases/<int:fase_id>/crear-cita/', views.crear_cita_desde_fase, name='crear_cita_desde_fase'),
    # Gestión de Pagos de Tratamiento
    path('planes-tratamiento/<int:plan_id>/pagos/registrar/', views.registrar_pago_tratamiento, name='registrar_pago_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/pagos/<int:pago_id>/eliminar/', views.eliminar_pago_tratamiento, name='eliminar_pago_tratamiento'),
    path('planes-tratamiento/<int:plan_id>/enviar-documentos/', views.enviar_documentos_tratamiento, name='enviar_documentos_tratamiento'),
    
    # Gestión de proveedores
    path('proveedores/', views_proveedores.gestor_proveedores, name='gestor_proveedores'),
    path('proveedores/crear/', views_proveedores.crear_proveedor, name='crear_proveedor'),
    path('proveedores/<int:proveedor_id>/editar/', views_proveedores.editar_proveedor, name='editar_proveedor'),
    path('proveedores/<int:proveedor_id>/eliminar/', views_proveedores.eliminar_proveedor, name='eliminar_proveedor'),
    path('proveedores/solicitud/enviar/', views_proveedores.enviar_solicitud_insumo, name='enviar_solicitud_insumo'),
    path('solicitudes/<int:solicitud_id>/marcar-recibida/', views_proveedores.marcar_solicitud_recibida, name='marcar_solicitud_recibida'),
    
    # Gestión de pedidos
    path('pedidos/', views_proveedores.gestor_pedidos, name='gestor_pedidos'),
    path('pedidos/crear/', views_proveedores.crear_pedido, name='crear_pedido'),
    path('api/insumos-proveedor/<int:proveedor_id>/', views_proveedores.obtener_insumos_proveedor, name='obtener_insumos_proveedor'),
    path('pedidos/<int:pedido_id>/', views_proveedores.detalle_pedido, name='detalle_pedido'),
    path('pedidos/<int:pedido_id>/agregar-insumo/', views_proveedores.agregar_insumo_pedido, name='agregar_insumo_pedido'),
    path('pedidos/<int:pedido_id>/enviar-correo/', views_proveedores.enviar_pedido_correo, name='enviar_pedido_correo'),
    
    # Gestión de servicios
    path('servicios/', views.gestor_servicios, name='gestor_servicios'),
    path('servicios/crear/', views.crear_servicio, name='crear_servicio'),
    path('servicios/<int:servicio_id>/editar/', views.editar_servicio, name='editar_servicio'),
    path('servicios/<int:servicio_id>/eliminar/', views.eliminar_servicio, name='eliminar_servicio'),
    
    # Gestión de horarios de dentistas
    path('horarios/', views.gestor_horarios, name='gestor_horarios'),
    path('horarios/dentista/<int:dentista_id>/', views.gestionar_horario_dentista, name='gestionar_horario_dentista'),
    path('horarios/dentista/<int:dentista_id>/agregar/', views.agregar_horario_ajax, name='agregar_horario_ajax'),
    path('horarios/<int:horario_id>/editar/', views.editar_horario_ajax, name='editar_horario_ajax'),
    path('horarios/dentista/<int:dentista_id>/eliminar/', views.eliminar_horarios_ajax, name='eliminar_horarios_ajax'),
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
    path('clientes/validar-email/', views.validar_email, name='validar_email'),
    path('clientes/buscar-por-email/', views.buscar_cliente_por_email, name='buscar_cliente_por_email'),
    path('clientes/validar-rut/', views.validar_rut, name='validar_rut'),
    path('clientes/validar-telefono/', views.validar_telefono, name='validar_telefono'),
    path('clientes/crear/', views.crear_cliente_presencial, name='crear_cliente_presencial'),
    path('clientes/sincronizar-web/', views.sincronizar_cliente_web, name='sincronizar_cliente_web'),
    path('clientes/<int:cliente_id>/', views.perfil_cliente, name='perfil_cliente'),
    path('clientes/<int:cliente_id>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:cliente_id>/obtener/', views.obtener_cliente, name='obtener_cliente'),
    path('clientes/<int:cliente_id>/citas/', views.obtener_citas_cliente, name='obtener_citas_cliente'),
    path('clientes/<int:cliente_id>/toggle-estado/', views.toggle_estado_cliente, name='toggle_estado_cliente'),
    path('clientes/<int:cliente_id>/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),
    
    # Gestión de documentos
    path('documentos/', views.gestor_documentos, name='gestor_documentos'),
    path('documentos/<int:documento_id>/descargar/', views.descargar_documento, name='descargar_documento'),
    path('documentos/<int:documento_id>/enviar-correo/', views.enviar_documento_correo, name='enviar_documento_correo'),
    path('planes-tratamiento/<int:plan_id>/exportar-pdf/', views.exportar_presupuesto_pdf, name='exportar_presupuesto_pdf'),
    
    # Auditoría
    path('auditoria/', views_auditoria.gestor_auditoria, name='gestor_auditoria'),
    
    # Gestión de consentimientos informados
    path('consentimientos/', views.gestor_consentimientos, name='gestor_consentimientos'),
    path('consentimientos/crear/', views.crear_consentimiento, name='crear_consentimiento'),
    path('planes-tratamiento/<int:plan_id>/consentimiento/crear/', views.crear_consentimiento_desde_plan, name='crear_consentimiento_desde_plan'),
    path('consentimientos/<int:consentimiento_id>/', views.detalle_consentimiento, name='detalle_consentimiento'),
    path('consentimientos/<int:consentimiento_id>/editar/', views.editar_consentimiento, name='editar_consentimiento'),
    path('consentimientos/<int:consentimiento_id>/firmar/', views.firmar_consentimiento, name='firmar_consentimiento'),
    path('consentimientos/<int:consentimiento_id>/eliminar/', views.eliminar_consentimiento, name='eliminar_consentimiento'),
    path('planes-tratamiento/<int:plan_id>/consentimiento/<int:consentimiento_id>/firmar-recepcion/', views.firmar_consentimiento_recepcion, name='firmar_consentimiento_recepcion'),
    path('consentimientos/<int:consentimiento_id>/descargar-documento-firmado/', views.descargar_documento_firmado_consentimiento, name='descargar_documento_firmado_consentimiento'),
    path('consentimientos/<int:consentimiento_id>/enviar-correo/', views.enviar_consentimiento_por_correo, name='enviar_consentimiento_por_correo'),
    path('consentimientos/<int:consentimiento_id>/exportar-pdf/', views.exportar_consentimiento_pdf, name='exportar_consentimiento_pdf'),
    path('consentimientos/plantilla/<int:plantilla_id>/', views.obtener_plantilla_consentimiento, name='obtener_plantilla_consentimiento'),
    
    # Firma pública (sin autenticación, usando token)
    path('consentimientos/firmar-publico/<str:token>/', views.firmar_consentimiento_publico, name='firmar_consentimiento_publico'),
    
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
