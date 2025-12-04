# Generated manually to fix remaining ForeignKeys pointing to citas_cliente

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0045_fix_cliente_foreign_key'),
    ]

    operations = [
        migrations.RunSQL(
            # Corregir citas_mensaje.cliente_id
            """
            DO $$
            BEGIN
                -- Verificar que la tabla existe antes de intentar modificar
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'citas_mensaje'
                ) THEN
                    -- Eliminar constraint antigua si existe
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'citas_mensaje_cliente_id_d89a66ce_fk_citas_cliente_id'
                    ) THEN
                        ALTER TABLE citas_mensaje 
                        DROP CONSTRAINT citas_mensaje_cliente_id_d89a66ce_fk_citas_cliente_id;
                    END IF;
                    
                    -- Crear nueva constraint apuntando a pacientes_cliente
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'citas_mensaje_cliente_id_fk_pacientes_cliente_id'
                    ) THEN
                        ALTER TABLE citas_mensaje
                        ADD CONSTRAINT citas_mensaje_cliente_id_fk_pacientes_cliente_id
                        FOREIGN KEY (cliente_id) 
                        REFERENCES pacientes_cliente(id) 
                        ON DELETE SET NULL 
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        migrations.RunSQL(
            # Corregir citas_odontograma.cliente_id
            """
            DO $$
            BEGIN
                -- Verificar que la tabla existe antes de intentar modificar
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'citas_odontograma'
                ) THEN
                    -- Eliminar constraint antigua si existe
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'citas_odontograma_cliente_id_ceaa33a7_fk_citas_cliente_id'
                    ) THEN
                        ALTER TABLE citas_odontograma 
                        DROP CONSTRAINT citas_odontograma_cliente_id_ceaa33a7_fk_citas_cliente_id;
                    END IF;
                    
                    -- Crear nueva constraint apuntando a pacientes_cliente
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'citas_odontograma_cliente_id_fk_pacientes_cliente_id'
                    ) THEN
                        ALTER TABLE citas_odontograma
                        ADD CONSTRAINT citas_odontograma_cliente_id_fk_pacientes_cliente_id
                        FOREIGN KEY (cliente_id) 
                        REFERENCES pacientes_cliente(id) 
                        ON DELETE SET NULL 
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        migrations.RunSQL(
            # Corregir citas_radiografia.cliente_id
            """
            DO $$
            BEGIN
                -- Verificar que la tabla existe antes de intentar modificar
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'citas_radiografia'
                ) THEN
                    -- Eliminar constraint antigua si existe
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'citas_radiografia_cliente_id_6fb3e33a_fk_citas_cliente_id'
                    ) THEN
                        ALTER TABLE citas_radiografia 
                        DROP CONSTRAINT citas_radiografia_cliente_id_6fb3e33a_fk_citas_cliente_id;
                    END IF;
                    
                    -- Crear nueva constraint apuntando a pacientes_cliente
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'citas_radiografia_cliente_id_fk_pacientes_cliente_id'
                    ) THEN
                        ALTER TABLE citas_radiografia
                        ADD CONSTRAINT citas_radiografia_cliente_id_fk_pacientes_cliente_id
                        FOREIGN KEY (cliente_id) 
                        REFERENCES pacientes_cliente(id) 
                        ON DELETE SET NULL 
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
    ]
