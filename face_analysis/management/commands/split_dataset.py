"""Django management command to split datasets into train/test/validation."""
from pathlib import Path

from django.core.management.base import BaseCommand

from face_analysis.utils.dataset_splitter import DatasetSplitter


class Command(BaseCommand):
    help = "Split dataset folders into train, validation, and test sets"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            type=str,
            required=True,
            help="Source directory containing class folders (e.g., face_analysis/datasets/skin_concerns)",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Output directory (if not specified, reorganizes in place)",
        )
        parser.add_argument(
            "--train-ratio",
            type=float,
            default=0.7,
            help="Ratio for training set (default: 0.7)",
        )
        parser.add_argument(
            "--val-ratio",
            type=float,
            default=0.15,
            help="Ratio for validation set (default: 0.15)",
        )
        parser.add_argument(
            "--test-ratio",
            type=float,
            default=0.15,
            help="Ratio for test set (default: 0.15)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility (default: 42)",
        )
        parser.add_argument(
            "--keep-original",
            action="store_true",
            help="Keep original class folders after splitting",
        )

    def handle(self, *args, **options):
        source_dir = Path(options["source_dir"])
        output_dir = Path(options["output_dir"]) if options["output_dir"] else None
        train_ratio = options["train_ratio"]
        val_ratio = options["val_ratio"]
        test_ratio = options["test_ratio"]
        seed = options["seed"]
        keep_original = options["keep_original"]

        # Validate source directory
        if not source_dir.exists():
            self.stdout.write(
                self.style.ERROR(f"Source directory does not exist: {source_dir}")
            )
            return

        # Create splitter
        splitter = DatasetSplitter(
            source_dir=source_dir,
            output_dir=output_dir,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed,
        )

        # Reorganize dataset
        self.stdout.write(
            self.style.SUCCESS(f"Reorganizing dataset from {source_dir}...")
        )

        try:
            statistics = splitter.reorganize_dataset(keep_original=keep_original)
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDataset reorganization completed successfully!\n"
                    f"Output directory: {splitter.output_dir}\n"
                    f"Total images split: {sum(statistics['total'].values())}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            raise

