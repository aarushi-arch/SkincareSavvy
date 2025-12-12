"""Django management command to train CNN models."""
from pathlib import Path

from django.core.management.base import BaseCommand

from face_analysis.training.trainer import CNNTrainer


class Command(BaseCommand):
    help = "Train CNN models for skin type or skin concern classification"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset-type",
            type=str,
            choices=["skin_types", "skin_concerns"],
            required=True,
            help="Type of dataset to train on (skin_types or skin_concerns)",
        )
        parser.add_argument(
            "--dataset-path",
            type=str,
            required=True,
            help="Path to the dataset directory",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default="face_analysis/models",
            help="Directory to save trained models (default: face_analysis/models)",
        )
        parser.add_argument(
            "--base-model",
            type=str,
            choices=["mobilenet", "resnet50", "vgg16", "custom"],
            default="mobilenet",
            help="Base model architecture (default: mobilenet)",
        )
        parser.add_argument(
            "--epochs",
            type=int,
            default=50,
            help="Number of training epochs (default: 50)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=32,
            help="Batch size for training (default: 32)",
        )
        parser.add_argument(
            "--learning-rate",
            type=float,
            default=0.001,
            help="Learning rate (default: 0.001)",
        )
        parser.add_argument(
            "--dropout-rate",
            type=float,
            default=0.5,
            help="Dropout rate (default: 0.5)",
        )
        parser.add_argument(
            "--image-size",
            type=int,
            nargs=2,
            default=[224, 224],
            help="Image size as height width (default: 224 224)",
        )

    def handle(self, *args, **options):
        dataset_type = options["dataset_type"]
        dataset_path = Path(options["dataset_path"])
        output_dir = Path(options["output_dir"])
        base_model = options["base_model"]
        epochs = options["epochs"]
        batch_size = options["batch_size"]
        learning_rate = options["learning_rate"]
        dropout_rate = options["dropout_rate"]
        image_size = tuple(options["image_size"])

        # Validate dataset path
        if not dataset_path.exists():
            self.stdout.write(
                self.style.ERROR(f"Dataset path does not exist: {dataset_path}")
            )
            return

        # Create trainer
        trainer = CNNTrainer(
            dataset_path=dataset_path,
            model_type=dataset_type,
            output_dir=output_dir,
            image_size=image_size,
            batch_size=batch_size,
            base_model=base_model,
            epochs=epochs,
            learning_rate=learning_rate,
            dropout_rate=dropout_rate,
        )

        # Prepare data
        self.stdout.write(self.style.SUCCESS("Preparing data..."))
        train_gen, val_gen, test_gen = trainer.prepare_data()

        # Build model
        self.stdout.write(self.style.SUCCESS("Building model..."))
        trainer.build_model()

        # Train model
        self.stdout.write(self.style.SUCCESS("Training model..."))
        trainer.train(train_gen, val_gen)

        # Evaluate model
        self.stdout.write(self.style.SUCCESS("Evaluating model..."))
        test_results = trainer.evaluate(test_gen)
        self.stdout.write(
            self.style.SUCCESS(
                f"Test accuracy: {test_results[1]:.4f}, Test loss: {test_results[0]:.4f}"
            )
        )

        # Save model and history
        self.stdout.write(self.style.SUCCESS("Saving model..."))
        trainer.save_model()
        trainer.save_training_history()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTraining completed! Model saved to {output_dir}"
            )
        )

