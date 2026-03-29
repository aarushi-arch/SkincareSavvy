"""Management command to activate skin concerns model."""
from django.core.management.base import BaseCommand
from face_analysis.models import CNNModel


class Command(BaseCommand):
    help = 'Activate a skin concerns model for face analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            'model_id',
            type=int,
            help='ID of the skin concerns model to activate'
        )

    def handle(self, *args, **options):
        model_id = options['model_id']
        
        try:
            model = CNNModel.objects.get(pk=model_id, model_type='skin_concerns')
        except CNNModel.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Skin concerns model with ID {model_id} not found')
            )
            return

        if not model.class_names_file:
            self.stdout.write(
                self.style.WARNING(
                    f'{model.name} is missing class_names_file. '
                    f'Please upload it before activating.'
                )
            )
            return

        if not model.model_file:
            self.stdout.write(
                self.style.ERROR(f'{model.name} is missing model_file')
            )
            return

        model.is_active = True
        model.save()

        self.stdout.write(
            self.style.SUCCESS(f'Activated skin concerns model: {model.name}')
        )
