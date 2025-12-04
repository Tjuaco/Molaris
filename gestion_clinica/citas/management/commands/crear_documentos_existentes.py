from django.core.management.base import BaseCommand
from historial_clinico.models import Odontograma, PlanTratamiento, DocumentoCliente
from pacientes.models import Cliente
from personal.models import Perfil
from django.utils import timezone


class Command(BaseCommand):
    help = 'Crea documentos para odontogramas y planes de tratamiento existentes que no tienen documento asociado'

    def handle(self, *args, **options):
        # Crear documentos para odontogramas
        odontogramas = Odontograma.objects.all()
        creados_odontograma = 0
        
        for odontograma in odontogramas:
            # Verificar si ya existe un documento para este odontograma
            if not DocumentoCliente.objects.filter(odontograma=odontograma, tipo='odontograma').exists():
                # Buscar cliente por email si no está asociado directamente
                cliente_doc = odontograma.cliente
                if not cliente_doc and odontograma.paciente_email:
                    try:
                        cliente_doc = Cliente.objects.get(email=odontograma.paciente_email, activo=True)
                    except Cliente.DoesNotExist:
                        cliente_doc = None
                    except Cliente.MultipleObjectsReturned:
                        cliente_doc = Cliente.objects.filter(email=odontograma.paciente_email, activo=True).first()
                
                # Obtener el dentista como generador
                generado_por = odontograma.dentista if odontograma.dentista else None
                
                DocumentoCliente.objects.create(
                    cliente=cliente_doc,
                    tipo='odontograma',
                    titulo=f'Ficha Odontológica - {odontograma.paciente_nombre}',
                    descripcion=f'Ficha odontológica del paciente {odontograma.paciente_nombre}',
                    odontograma=odontograma,
                    generado_por=generado_por,
                    fecha_generacion=odontograma.fecha_creacion
                )
                creados_odontograma += 1
        
        # Crear documentos para planes de tratamiento
        planes = PlanTratamiento.objects.all()
        creados_presupuestos = 0
        
        for plan in planes:
            # Verificar si ya existe un documento para este plan
            if not DocumentoCliente.objects.filter(plan_tratamiento=plan, tipo='presupuesto').exists():
                DocumentoCliente.objects.create(
                    cliente=plan.cliente,
                    tipo='presupuesto',
                    titulo=f'Presupuesto - {plan.nombre}',
                    descripcion=f'Presupuesto del tratamiento {plan.nombre}',
                    plan_tratamiento=plan,
                    generado_por=plan.creado_por,
                    fecha_generacion=plan.creado_el
                )
                creados_presupuestos += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Creados {creados_odontograma} documentos de odontogramas\n'
                f'✓ Creados {creados_presupuestos} documentos de presupuestos\n'
                f'✓ Total: {creados_odontograma + creados_presupuestos} documentos creados'
            )
        )


