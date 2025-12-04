# Análisis del Flujo entre gestion_clinica y cliente_web

## Arquitectura General

Ambos proyectos (`gestion_clinica` y `cliente_web`) comparten la **misma base de datos PostgreSQL**, lo que permite sincronización directa entre sistemas.

## Tablas Compartidas

### 1. `citas_cita`
- **Modelo en gestion_clinica**: `citas.models.Cita`
- **Modelo en cliente_web**: `reservas.models.Cita` (con `db_table = "citas_cita"`)
- **Relaciones**:
  - `cliente_id` → ForeignKey a `pacientes_cliente` (en gestion_clinica)
  - `dentista_id` → ForeignKey a `personal_perfil` (en gestion_clinica)
  - Campos de respaldo: `paciente_nombre`, `paciente_email`, `paciente_telefono`

### 2. `pacientes_cliente` (o `citas_cliente`)
- **Modelo en gestion_clinica**: `pacientes.models.Cliente`
- **Modelo en cliente_web**: `reservas.documentos_models.ClienteDocumento` (con `managed = False`)
- **Campos clave**: `nombre_completo`, `email`, `telefono`, `rut`, `fecha_nacimiento`, `alergias`, `activo`

### 3. `auth_user`
- **Modelo**: Django `User` (estándar)
- Usado por ambos sistemas para autenticación

### 4. `cuentas_perfilcliente`
- **Modelo en cliente_web**: `cuentas.models.PerfilCliente`
- **Relación**: `user_id` → OneToOneField a `auth_user` con `on_delete=CASCADE`
- **NO tiene relación directa con `pacientes_cliente`**

## Flujo de Sincronización

### A. Creación de Cliente desde gestion_clinica

**Proceso:**
1. Usuario administrativo crea un `Cliente` en `gestion_clinica`
2. Si se marca "Enviar credenciales por correo":
   - Se crea un `User` en Django
   - Se crea/actualiza un `PerfilCliente` en `cuentas_perfilcliente` (usando SQL directo)
   - Se envía email con credenciales

**Código relevante:**
- `gestion_clinica/citas/views.py` → `crear_cliente_presencial()`

**Problemas potenciales:**
- Si falla la creación de `PerfilCliente`, el `User` queda huérfano
- Si falla el envío de email, el usuario no sabe sus credenciales

### B. Registro de Cliente desde cliente_web

**Proceso:**
1. Usuario se registra en `cliente_web`
2. Se crea un `User` en Django
3. Se crea un `PerfilCliente` en `cuentas_perfilcliente`
4. Se intenta crear automáticamente un `Cliente` en `pacientes_cliente` (usando import directo)

**Código relevante:**
- `cliente_web/cuentas/views.py` → `registro_cliente()`

**Problemas potenciales:**
- Si falla la creación del `Cliente`, el `PerfilCliente` queda sin `Cliente` asociado
- No hay validación de duplicados antes de crear

### C. Reserva de Cita desde cliente_web

**Proceso:**
1. Usuario reserva una cita disponible
2. Se busca o crea un `Cliente` en `pacientes_cliente` (usando SQL directo)
3. Se actualiza la `Cita` con `cliente_id` y datos del paciente
4. Se envía SMS/WhatsApp de confirmación

**Código relevante:**
- `cliente_web/reservas/views.py` → `reservar_cita()`

**Problemas potenciales:**
- Si el `Cliente` se crea pero la actualización de la cita falla, hay inconsistencia
- No se valida si el `Cliente` ya existe con datos diferentes

### D. Asignación de Cita desde gestion_clinica

**Proceso:**
1. Usuario administrativo asigna una cita a un `Cliente`
2. Se actualiza la `Cita` con `cliente_id`
3. Se envían notificaciones (WhatsApp/SMS)

**Código relevante:**
- `gestion_clinica/citas/views.py` → múltiples funciones de creación/edición de citas

## Problemas Identificados

### 1. Eliminación de Cliente

**Problema:**
- Al eliminar un `Cliente`, no se eliminan automáticamente el `User` y `PerfilCliente` asociados
- No hay relación ForeignKey entre `Cliente` y `User`/`PerfilCliente`
- La eliminación debe hacerse manualmente en el código

**Solución implementada:**
- `eliminar_cliente()` busca el `User` por email y username
- Elimina `PerfilCliente` usando SQL directo
- Elimina el `User`
- Si no encuentra por email/username, busca `PerfilCliente` directamente por email

### 2. Registros Huérfanos

**Problema:**
- `PerfilCliente` sin `Cliente` activo asociado
- `User` sin `Cliente` activo asociado
- Pueden quedar después de eliminaciones fallidas o errores en sincronización

**Solución:**
- Script `limpiar_registros_huerfanos.py` para identificar y eliminar registros huérfanos

### 3. Validación de Duplicados

**Problema:**
- No hay validación consistente entre sistemas
- Un email puede existir en `Cliente` pero no en `User`, o viceversa

**Solución implementada:**
- Validación en `crear_cliente_presencial()` que verifica:
  - Email en `Cliente` activo
  - Email en `User` con `Cliente` activo asociado
  - RUT en `Cliente` activo
  - Teléfono en `Cliente` activo

### 4. Sincronización de Datos

**Problema:**
- Los datos pueden desincronizarse entre `Cliente` y `PerfilCliente`
- No hay mecanismo automático de sincronización

**Recomendación:**
- Implementar un comando de sincronización periódica
- O usar señales de Django para mantener sincronizados

## Mejoras Implementadas ✅

### 1. Relación Explícita ✅
- ✅ Agregado campo `user` (OneToOneField) opcional en `Cliente` para relacionar directamente
- ✅ Facilita la eliminación en cascada y la sincronización
- ✅ Migración creada: `pacientes/migrations/0003_add_user_field_to_cliente.py`

### 2. Transacciones Atómicas ✅
- ✅ Implementado `transaction.atomic()` en `crear_cliente_presencial()` para crear Cliente, User y PerfilCliente
- ✅ Implementado `transaction.atomic()` en `eliminar_cliente()` para eliminar User y PerfilCliente
- ✅ Asegura que si falla una parte, se revierta todo

### 3. Logging Mejorado ✅
- ✅ Logging detallado en todas las operaciones de sincronización
- ✅ Logging de éxito, advertencias y errores con emojis para fácil identificación
- ✅ Facilita el debugging de problemas

### 4. Validación Centralizada ✅
- ✅ Creado módulo `citas/validaciones.py` con funciones reutilizables:
  - `validar_email_cliente()`: Valida email en Cliente activo
  - `validar_rut_cliente()`: Valida RUT en Cliente activo
  - `validar_telefono_cliente()`: Valida teléfono en Cliente activo
  - `validar_username_disponible()`: Valida username disponible
  - `validar_datos_cliente_completos()`: Valida todos los datos de una vez
- ✅ Funciones usadas en `crear_cliente_presencial()` y disponibles para ambos sistemas

## Flujo de Eliminación Mejorado

```
eliminar_cliente(cliente_id):
  1. Obtener email y username del Cliente
  2. Buscar User por email Y username
  3. Si encuentra User:
     a. Eliminar PerfilCliente (SQL directo)
     b. Eliminar User
  4. Si NO encuentra User:
     a. Buscar PerfilCliente por email (SQL directo)
     b. Si encuentra, obtener user_id
     c. Eliminar PerfilCliente
     d. Eliminar User asociado
  5. Actualizar citas relacionadas (cliente = None, estado = 'disponible')
  6. Eliminar Cliente
  7. Registrar en auditoría
```

## Scripts de Mantenimiento

### `limpiar_registros_huerfanos.py`
- Identifica `PerfilCliente` sin `Cliente` activo
- Identifica `User` sin `Cliente` activo (excepto staff/admin)
- Permite eliminación segura con `--dry-run` y `--force`

### Uso:
```bash
# Ver qué se eliminaría
python limpiar_registros_huerfanos.py --dry-run

# Eliminar con confirmación
python limpiar_registros_huerfanos.py

# Eliminar sin confirmación
python limpiar_registros_huerfanos.py --force
```

