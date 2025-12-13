from io import BytesIO
from pathlib import Path

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from PIL import Image, UnidentifiedImageError

from .forms import CNNModelUploadForm
from .models import CNNModel
from .services.cnn import FaceAnalysisPipeline


# Initialize pipeline - will load models if they exist
pipeline = FaceAnalysisPipeline()


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
                
                # Try to analyze the image
                try:
                    analysis_result = pipeline.analyze(image_bytes)
                    
                    # Check if analysis returned errors
                    if analysis_result and isinstance(analysis_result, dict):
                        if analysis_result.get("skin_type", {}).get("error"):
                            error = f"Skin type analysis error: {analysis_result['skin_type']['error']}"
                        if analysis_result.get("skin_concerns", {}).get("error"):
                            if error:
                                error += f" | Skin concerns error: {analysis_result['skin_concerns']['error']}"
                            else:
                                error = f"Skin concerns error: {analysis_result['skin_concerns']['error']}"
                    
                    # If no results and no errors, provide a message
                    if not analysis_result or (not analysis_result.get("skin_type") and not analysis_result.get("skin_concerns")):
                        error = "Analysis completed but no results were returned. Models may not be loaded."
                        
                except Exception as analysis_exc:
                    error = f"Analysis failed: {str(analysis_exc)}"

            except UnidentifiedImageError:
                error = "Uploaded file is not a valid image."
            except Exception as exc:
                error = f"Could not process the image: {str(exc)}"

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
