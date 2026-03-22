"""Management command to check and activate CNN models."""
from django.core.management.base import BaseCommand, CommandError
from face_analysis.models import CNNModel


class Command(BaseCommand):
    help = 'Check CNN model status and activate skin concerns model'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== CNN Model Status ===\n'))

        # Check skin types model
        skin_types_active = CNNModel.objects.filter(
            model_type='skin_types',
            is_active=True
        ).first()

        if skin_types_active:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Skin Types Model Active: {skin_types_active.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING('✗ No active Skin Types model')
            )
            skin_types = CNNModel.objects.filter(model_type='skin_types')
            if skin_types.exists():
                self.stdout.write('  Available:', ' | '.join([m.name for m in skin_types]))

        # Check skin concerns model
        self.stdout.write('\n')
        skin_concerns_active = CNNModel.objects.filter(
            model_type='skin_concerns',
            is_active=True
        ).first()

        if skin_concerns_active:
            status = '✓' if skin_concerns_active.class_names else '✗'
            class_names_status = 'Yes' if skin_concerns_active.class_names else 'NO CLASS NAMES FILE'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{status} Skin Concerns Model Active: {skin_concerns_active.name} '
                    f'(Class names: {class_names_status})'
                )
            )
            if not skin_concerns_active.class_names:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ {skin_concerns_active.name} is missing class_names_file!'
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING('✗ No active Skin Concerns model')
            )
            skin_concerns = CNNModel.objects.filter(model_type='skin_concerns')
            if skin_concerns.exists():
                self.stdout.write('  Available models:')
                for model in skin_concerns:
                    ready = '✓' if model.class_names else '✗ (missing class names)'
                    self.stdout.write(f'    {ready} {model.name}')
            else:
                self.stdout.write(self.style.ERROR('  No skin concerns models found!'))

        # Offer to activate
        self.stdout.write('\n')
        skin_concerns = CNNModel.objects.filter(
            model_type='skin_concerns'
        ).exclude(is_active=True)

        if skin_concerns.exists():
            self.stdout.write('To activate a skin concerns model, use:')
            for model in skin_concerns:
                ready = '(ready)' if model.class_names else '(MISSING CLASS NAMES - do this first)'
                self.stdout.write(
                    f'  python manage.py shell -c '
                    f'"from face_analysis.models import CNNModel; '
                    f'm = CNNModel.objects.get(pk={model.pk}); '
                    f'm.is_active = True; m.save()" {ready}'
                )
