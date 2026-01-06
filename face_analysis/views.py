import base64
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from PIL import Image, UnidentifiedImageError

from .forms import CNNModelUploadForm
from .models import CNNModel
from .services.cnn import FaceAnalysisPipeline
from recommendations.utils import recommend_products, build_routine
from .analyze_face import analyze_face


# Initialize pipeline (models will be loaded lazily)
pipeline = FaceAnalysisPipeline()


def index(request):
    """
    Main face analysis page.
    Handles image upload and runs CNN analysis.
    """
    analysis_result = None
    error = None

    recommended_products = []
    routine = None

    if request.method == "POST":
        uploaded_file = request.FILES.get("face_image")

        if not uploaded_file:
            error = "Please upload an image."
        else:
            try:
                # Validate uploaded image
                image = Image.open(uploaded_file)
                image.verify()
                uploaded_file.seek(0)

                image_bytes = uploaded_file.read()

                # Run analysis
                analysis_result = analyze_face(image_bytes)
                
                # Add image to result for display in template
                if analysis_result:
                    analysis_result["image_base64"] = base64.b64encode(image_bytes).decode('utf-8')
                
                # Fetch Recommendations
                if analysis_result:
                    # Extract Data
                    skin_type = ""
                    concerns = []
                    
                    if "skin_type" in analysis_result and "predictions" in analysis_result["skin_type"]:
                        preds = analysis_result["skin_type"]["predictions"]
                        if preds:
                            skin_type = preds[0]["class"]
                            
                    if "skin_concerns" in analysis_result and "predictions" in analysis_result["skin_concerns"]:
                        preds = analysis_result["skin_concerns"]["predictions"]
                        concerns = [p["class"] for p in preds]
                    
                    query = {
                        "skin_type": skin_type,
                        "concerns": concerns
                    }
                    
                    recommended_products = recommend_products(query)
                    routine = build_routine(query)
                    print(f"Found {len(recommended_products)} products and built personalized routine.")

                # DEBUG OUTPUT (VERY IMPORTANT)
                print("ANALYSIS RESULT:", analysis_result)

            except UnidentifiedImageError:
                error = "The uploaded file is not a valid image."
            except Exception as e:
                error = f"Analysis failed: {str(e)}"
                import traceback
                traceback.print_exc()

    return render(
        request,
        "face_analysis/index.html",
        {
            "analysis_result": analysis_result,
            "recommended_products": recommended_products,
            "routine": routine,
            "error": error,
        },
    )


def upload_model(request):
    """
    Upload a trained CNN model and related JSON files.
    """
    if request.method == "POST":
        form = CNNModelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            model = form.save()
            messages.success(
                request,
                f"Model '{model.name}' uploaded successfully!"
            )
            return redirect("face_analysis:model_list")
    else:
        form = CNNModelUploadForm()

    return render(
        request,
        "face_analysis/upload_model.html",
        {"form": form},
    )


class ModelListView(ListView):
    """
    List all uploaded CNN models.
    """
    model = CNNModel
    template_name = "face_analysis/model_list.html"
    context_object_name = "models"
    paginate_by = 10


def model_detail(request, pk):
    """
    View details of a single CNN model.
    """
    model = get_object_or_404(CNNModel, pk=pk)
    return render(
        request,
        "face_analysis/model_detail.html",
        {"model": model},
    )


def delete_model(request, pk):
    """
    Delete a CNN model.
    """
    model = get_object_or_404(CNNModel, pk=pk)

    if request.method == "POST":
        model_name = model.name
        model.delete()
        messages.success(
            request,
            f"Model '{model_name}' deleted successfully!"
        )
        return redirect("face_analysis:model_list")

    return render(
        request,
        "face_analysis/model_confirm_delete.html",
        {"model": model},
    )
