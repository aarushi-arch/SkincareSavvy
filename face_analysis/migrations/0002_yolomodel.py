from django.db import migrations, models
import django.core.validators
import face_analysis.models


class Migration(migrations.Migration):

    dependencies = [
        ('face_analysis', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='YOLOModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('model_file', models.FileField(
                    upload_to=face_analysis.models.yolo_model_upload_path,
                    validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pt'])],
                    help_text='Upload YOLO model weights (.pt)',
                )),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=False, help_text='Only one YOLO model should be active at a time')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'YOLO Model',
                'verbose_name_plural': 'YOLO Models',
                'ordering': ['-created_at'],
            },
        ),
    ]
