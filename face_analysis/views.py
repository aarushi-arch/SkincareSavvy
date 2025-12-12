from io import BytesIO

from django.shortcuts import render
from PIL import Image, UnidentifiedImageError

from .services.cnn import FaceAnalysisPipeline


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
