from io import BytesIO

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from PIL import Image, UnidentifiedImageError

from .forms import CNNModelUploadForm
from .models import CNNModel
from .services.cnn import FaceAnalysisPipeline


pipeline = FaceAnalysisPipeline(
    models_dir=Path("face_analysis/models/ml")
)


def index(request):
    """
    Landing view for the face analysis feature with upload handling.
    """
    analysis_result = None
    error = None

    if request.method == "POST":
        uploaded_file = request.FILES.get("face_image")
        if not uploaded_file:
            error = "Please upload a photo before submitting."
        else:
            try:
                # Validate that the uploaded file is an image
                img = Image.open(uploaded_file)
                img.verify()
                uploaded_file.seek(0)

                image_bytes = uploaded_file.read()
                analysis_result = pipeline.analyze(image_bytes)

            except UnidentifiedImageError:
                error = "Uploaded file is not a valid image."
            except Exception as exc:
                error = f"Could not analyze the image: {exc}"

    # REMOVE THE FALLBACK THAT WAS CAUSING THE ERROR

    context = {
        "analysis_result": analysis_result,
        "error": error,
    }
    return render(request, "face_analysis/index.html", context)


def upload_model(request):
    """View for uploading CNN model files."""
    if request.method == "POST":
        form = CNNModelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            model = form.save()
            messages.success(request, f"Model '{model.name}' uploaded successfully!")
            return redirect("face_analysis:model_list")
    else:
        form = CNNModelUploadForm()
    
    return render(request, "face_analysis/upload_model.html", {"form": form})


class ModelListView(ListView):
    """List view for uploaded CNN models."""
    model = CNNModel
    template_name = "face_analysis/model_list.html"
    context_object_name = "models"
    paginate_by = 10


def model_detail(request, pk):
    """Detail view for a CNN model."""
    model = get_object_or_404(CNNModel, pk=pk)
    return render(request, "face_analysis/model_detail.html", {"model": model})


def delete_model(request, pk):
    """Delete a CNN model."""
    model = get_object_or_404(CNNModel, pk=pk)
    if request.method == "POST":
        model_name = model.name
        model.delete()
        messages.success(request, f"Model '{model_name}' deleted successfully!")
        return redirect("face_analysis:model_list")
    return render(request, "face_analysis/model_confirm_delete.html", {"model": model})
