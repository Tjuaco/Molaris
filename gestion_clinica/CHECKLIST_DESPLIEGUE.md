# Checklist de Despliegue - Base de Datos

## Pre-requisitos

- [ ] ✅ No hay datos importantes en la base de datos (o se hizo backup)
- [ ] ✅ Todas las migraciones están en el repositorio
- [ ] ✅ El código está en la versión final
- [ ] ✅ Se probó en entorno de desarrollo

## Proceso de Reset y Verificación

### Paso 1: Reset Completo (Opcional pero Recomendado)

Si no hay datos importantes, ejecutar reset completo:

```bash
python reset_database_clean.py
```

Este script:
- ✅ Elimina todas las tablas
- ✅ Resetea el estado de migraciones
- ✅ Ejecuta todas las migraciones desde cero
- ✅ Verifica que la estructura esté correcta
- ✅ Permite crear superusuario

### Paso 2: Verificación de Estructura

Ejecutar verificación completa:

```bash
python verificar_estructura_bd.py
```

Verificar que:
- ✅ Todas las tablas críticas existen
- ✅ NO existe la tabla `citas_cliente` (obsoleta)
- ✅ Todas las ForeignKeys apuntan a las tablas correctas
- ✅ `citas_cita.cliente_id` → `pacientes_cliente.id`
- ✅ `citas_cita.dentista_id` → `personal_perfil.id`

### Paso 3: Verificar cliente_web

En el proyecto `cliente_web`, verificar:

1. **Modelo ClienteDocumento**:
   ```python
   # Debe usar pacientes_cliente
   db_table = 'pacientes_cliente'  # ✅ CORRECTO
   ```

2. **Ejecutar migraciones en cliente_web**:
   ```bash
   cd ../cliente_web
   python manage.py migrate
   ```

3. **Verificar que puede acceder a pacientes_cliente**:
   ```bash
   python manage.py shell
   >>> from reservas.documentos_models import ClienteDocumento
   >>> ClienteDocumento.objects.count()  # Debe funcionar sin error
   ```

### Paso 4: Crear Datos de Prueba (Opcional)

Si es necesario, crear datos de prueba:

```bash
python manage.py shell
```

```python
from pacientes.models import Cliente
from personal.models import Perfil
from citas.models import TipoServicio

# Crear cliente de prueba
cliente = Cliente.objects.create(
    nombre_completo="Cliente Prueba",
    email="prueba@test.com",
    telefono="+56912345678",
    activo=True
)

# Verificar que se creó correctamente
print(f"Cliente creado: {cliente.id}")
```

## Verificaciones Finales

### ✅ Estructura de Base de Datos

- [ ] Tabla `pacientes_cliente` existe y tiene la estructura correcta
- [ ] Tabla `citas_cliente` NO existe (o está vacía y sin referencias)
- [ ] Tabla `citas_cita` existe y tiene ForeignKeys correctas
- [ ] Todas las ForeignKeys apuntan a las tablas correctas

### ✅ Migraciones

- [ ] Todas las migraciones están aplicadas
- [ ] No hay migraciones pendientes
- [ ] Las migraciones 0045 y 0046 están aplicadas (correcciones de ForeignKeys)

### ✅ Modelos

- [ ] `gestion_clinica.pacientes.models.Cliente` usa `pacientes_cliente`
- [ ] `cliente_web.reservas.documentos_models.ClienteDocumento` usa `pacientes_cliente`
- [ ] `gestion_clinica.citas.models.Cita.cliente` apunta a `pacientes.models.Cliente`

### ✅ Funcionalidad

- [ ] Se puede crear un cliente desde `gestion_clinica`
- [ ] Se puede crear una cita y asignarle un cliente
- [ ] Se puede reservar una cita desde `cliente_web`
- [ ] No hay errores de ForeignKey al crear/editar citas

## Comandos Útiles

### Ver todas las tablas
```bash
python manage.py dbshell
\dt
```

### Ver ForeignKeys de una tabla
```sql
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS tabla_destino
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name = 'citas_cita';
```

### Verificar que no existe citas_cliente
```sql
SELECT 1 FROM information_schema.tables 
WHERE table_name = 'citas_cliente';
-- No debe devolver resultados
```

## Problemas Comunes y Soluciones

### Error: ForeignKey apunta a tabla incorrecta

**Solución**: Ejecutar migraciones 0045 y 0046:
```bash
python manage.py migrate citas 0046
```

### Error: Tabla citas_cliente existe

**Solución**: 
1. Verificar que no hay datos importantes
2. Verificar que no hay ForeignKeys apuntando a ella
3. Eliminar manualmente: `DROP TABLE citas_cliente CASCADE;`

### Error: cliente_web no puede acceder a pacientes_cliente

**Solución**: 
1. Verificar que `ClienteDocumento` usa `db_table = 'pacientes_cliente'`
2. Reiniciar el servidor de desarrollo
3. Verificar permisos de base de datos

## Listo para Despliegue

Una vez completado este checklist:

- ✅ Base de datos limpia y correcta
- ✅ Todas las ForeignKeys correctas
- ✅ Ambos sistemas pueden acceder a las tablas compartidas
- ✅ No hay inconsistencias estructurales

**La base de datos está lista para producción** 🚀


