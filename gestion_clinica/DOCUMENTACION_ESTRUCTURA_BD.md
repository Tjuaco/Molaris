# Documentación de Estructura de Base de Datos Compartida

## Resumen Ejecutivo

Este documento describe la estructura de la base de datos compartida entre `gestion_clinica` y `cliente_web`, y las correcciones aplicadas para asegurar consistencia.

## Tablas Compartidas Críticas

### 1. `pacientes_cliente` (TABLA PRINCIPAL)

**Estado**: ✅ Tabla correcta y en uso

- **Modelo en gestion_clinica**: `pacientes.models.Cliente`
- **Modelo en cliente_web**: `reservas.documentos_models.ClienteDocumento` (con `db_table = 'pacientes_cliente'`)
- **Campos principales**:
  - `id` (BigAutoField, PK)
  - `nombre_completo` (CharField, max_length=150)
  - `email` (EmailField, unique=True)
  - `telefono` (CharField, formato: +569XXXXXXXX)
  - `rut` (CharField, unique, nullable)
  - `fecha_nacimiento` (DateField, nullable)
  - `alergias` (TextField, nullable)
  - `activo` (BooleanField, default=True)
  - `user_id` (ForeignKey a auth_user, nullable)
  - `dentista_asignado_id` (ForeignKey a personal_perfil, nullable)

**ForeignKeys que apuntan a esta tabla**:
- ✅ `citas_cita.cliente_id` → `pacientes_cliente.id`
- ✅ `comunicacion_mensaje.cliente_id` → `pacientes_cliente.id`
- ✅ `evaluaciones_evaluacion.cliente_id` → `pacientes_cliente.id`
- ✅ `historial_clinico_odontograma.cliente_id` → `pacientes_cliente.id`
- ✅ `historial_clinico_radiografia.cliente_id` → `pacientes_cliente.id`
- ✅ `historial_clinico_plantratamiento.cliente_id` → `pacientes_cliente.id`
- ✅ `historial_clinico_documentocliente.cliente_id` → `pacientes_cliente.id`
- ✅ `historial_clinico_consentimientoinformado.cliente_id` → `pacientes_cliente.id`

### 2. `citas_cliente` (TABLA OBSOLETA)

**Estado**: ⚠️ Tabla obsoleta, debe eliminarse

- **Problema**: Esta tabla fue creada en migraciones antiguas pero ya no se usa
- **Solución**: 
  - Migrar datos a `pacientes_cliente` si existen
  - Corregir ForeignKeys que apunten a esta tabla
  - Eliminar la tabla una vez que no haya referencias

**ForeignKeys que apuntaban a esta tabla (CORREGIDAS)**:
- ❌ `citas_mensaje.cliente_id` → `citas_cliente.id` (CORREGIDA a `pacientes_cliente`)
- ❌ `citas_odontograma.cliente_id` → `citas_cliente.id` (CORREGIDA a `pacientes_cliente`)
- ❌ `citas_radiografia.cliente_id` → `citas_cliente.id` (CORREGIDA a `pacientes_cliente`)

### 3. `citas_cita`

**Estado**: ✅ Tabla correcta

- **Modelo en gestion_clinica**: `citas.models.Cita`
- **Modelo en cliente_web**: `reservas.models.Cita` (con `db_table = "citas_cita"`)
- **ForeignKeys críticas**:
  - ✅ `cliente_id` → `pacientes_cliente.id` (CORREGIDA)
  - ✅ `dentista_id` → `personal_perfil.id`
  - ✅ `creada_por_id` → `personal_perfil.id`
  - ✅ `tipo_servicio_id` → `citas_tiposervicio.id`

## Correcciones Aplicadas

### 1. Migración 0045_fix_cliente_foreign_key

**Archivo**: `gestion_clinica/citas/migrations/0045_fix_cliente_foreign_key.py`

**Acciones**:
- Elimina la ForeignKey incorrecta `citas_cita_cliente_id_c277d0e3_fk_citas_cliente_id`
- Crea la ForeignKey correcta `citas_cita_cliente_id_fk_pacientes_cliente_id`

### 2. Actualización de cliente_web

**Archivo**: `cliente_web/reservas/documentos_models.py`

**Cambio**:
```python
# ANTES (INCORRECTO):
db_table = 'citas_cliente'

# DESPUÉS (CORRECTO):
db_table = 'pacientes_cliente'
```

### 3. Scripts de Verificación y Corrección

**Scripts creados**:
1. `verificar_estructura_bd.py`: Analiza la estructura completa y detecta problemas
2. `corregir_estructura_bd.py`: Corrige automáticamente los problemas detectados

## Reglas de Uso

### ✅ HACER

1. **Siempre usar `pacientes_cliente`** para referencias a clientes
2. **Verificar ForeignKeys** antes de crear nuevas relaciones
3. **Usar transacciones** al crear/actualizar clientes desde ambos sistemas
4. **Validar datos** antes de insertar en `pacientes_cliente`

### ❌ NO HACER

1. **NO usar `citas_cliente`** - esta tabla está obsoleta
2. **NO crear ForeignKeys** apuntando a `citas_cliente`
3. **NO modificar directamente** la estructura sin migraciones
4. **NO asumir** que ambas tablas tienen los mismos datos

## Flujo de Sincronización

### Creación de Cliente desde gestion_clinica

```
1. Crear Cliente en pacientes_cliente
2. Si se envía credenciales:
   - Crear User en auth_user
   - Crear PerfilCliente en cuentas_perfilcliente (SQL directo)
   - Enviar email con credenciales
```

### Registro desde cliente_web

```
1. Crear User en auth_user
2. Crear PerfilCliente en cuentas_perfilcliente
3. Crear Cliente en pacientes_cliente (SQL directo)
4. Sincronizar datos entre PerfilCliente y Cliente
```

### Reserva de Cita

```
1. Buscar Cliente en pacientes_cliente por email/nombre
2. Si no existe, crear en pacientes_cliente
3. Actualizar Cita con cliente_id apuntando a pacientes_cliente
```

## Checklist de Despliegue

Antes de desplegar, verificar:

- [ ] ✅ Todas las ForeignKeys apuntan a `pacientes_cliente`
- [ ] ✅ `cliente_web` usa `pacientes_cliente` en `ClienteDocumento`
- [ ] ✅ La tabla `citas_cliente` está vacía o eliminada
- [ ] ✅ No hay ForeignKeys apuntando a `citas_cliente`
- [ ] ✅ Los datos están sincronizados entre sistemas
- [ ] ✅ Las migraciones están aplicadas en ambos proyectos

## Comandos Útiles

### Verificar estructura
```bash
python verificar_estructura_bd.py
```

### Corregir estructura
```bash
python corregir_estructura_bd.py
```

### Verificar ForeignKeys
```sql
SELECT 
    tc.table_name AS tabla_origen,
    kcu.column_name AS columna,
    ccu.table_name AS tabla_destino
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND ccu.table_name IN ('pacientes_cliente', 'citas_cliente')
ORDER BY tc.table_name;
```

## Notas Finales

- **Única fuente de verdad**: `pacientes_cliente` es la única tabla válida para clientes
- **Consistencia**: Todos los sistemas deben usar `pacientes_cliente`
- **Migraciones**: Siempre usar migraciones de Django para cambios estructurales
- **Validación**: Validar datos antes de insertar para evitar inconsistencias


