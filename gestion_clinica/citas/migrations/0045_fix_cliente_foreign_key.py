# Generated manually to fix ForeignKey pointing to wrong table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0044_fix_all_perfil_foreign_keys'),
    ]

    operations = [
        migrations.RunSQL(
            # Primero, eliminar la ForeignKey incorrecta si existe
            """
            DO $$
            BEGIN
                -- Eliminar la constraint de ForeignKey incorrecta si existe
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'citas_cita_cliente_id_c277d0e3_fk_citas_cliente_id'
                ) THEN
                    ALTER TABLE citas_cita 
                    DROP CONSTRAINT citas_cita_cliente_id_c277d0e3_fk_citas_cliente_id;
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        migrations.RunSQL(
            # Crear la ForeignKey correcta apuntando a pacientes_cliente
            """
            DO $$
            BEGIN
                -- Verificar que la tabla pacientes_cliente existe
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'pacientes_cliente'
                ) THEN
                    -- Crear la ForeignKey correcta
                    ALTER TABLE citas_cita
                    ADD CONSTRAINT citas_cita_cliente_id_fk_pacientes_cliente_id
                    FOREIGN KEY (cliente_id) 
                    REFERENCES pacientes_cliente(id) 
                    ON DELETE SET NULL 
                    DEFERRABLE INITIALLY DEFERRED;
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
    ]
