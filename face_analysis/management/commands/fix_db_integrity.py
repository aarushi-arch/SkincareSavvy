"""Management command to fix database integrity - ensure only one active model per type."""
from django.core.management.base import BaseCommand
from face_analysis.models import CNNModel


class Command(BaseCommand):
    help = 'Fix database integrity - ensure only one active model per type'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Fixing Database Integrity ===\n'))

        # Check skin_types
        skin_types_active = CNNModel.objects.filter(
            model_type='skin_types',
            is_active=True
        )
        if skin_types_active.count() > 1:
            self.stdout.write(self.style.WARNING(
                f'Found {skin_types_active.count()} active Skin Types models. Keeping first, deactivating others...'
            ))
            keep = skin_types_active.first()
            deactivate = skin_types_active.exclude(pk=keep.pk)
            for model in deactivate:
                model.is_active = False
                model.save()
                self.stdout.write(f"   Deactivated: {model.name}")
            self.stdout.write(self.style.SUCCESS(f'   Kept active: {keep.name}\n'))

        # Check skin_concerns
        skin_concerns_active = CNNModel.objects.filter(
            model_type='skin_concerns',
            is_active=True
        )
        if skin_concerns_active.count() > 1:
            self.stdout.write(self.style.WARNING(
                f'Found {skin_concerns_active.count()} active Skin Concerns models. Keeping first, deactivating others...'
            ))
            keep = skin_concerns_active.first()
            deactivate = skin_concerns_active.exclude(pk=keep.pk)
            for model in deactivate:
                model.is_active = False
                model.save()
                self.stdout.write(f"   Deactivated: {model.name}")
            self.stdout.write(self.style.SUCCESS(f'   Kept active: {keep.name}\n'))

        self.stdout.write(self.style.SUCCESS(' Database integrity restored!'))
