import base64
import json
import numpy as np
import cv2
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from PIL import Image, UnidentifiedImageError

from .forms import CNNModelUploadForm
from .models import CNNModel
from .routine_builder import build_routine
from .services.cnn import FaceAnalysisPipeline
from .services.yolo_pipeline import YOLOAnalysisPipeline
from .services.unified_pipeline import analyze as unified_analyze
from .utils.skin_explanation import generate_skin_explanation
from .utils.ingredient_recommender import get_advice as get_ingredient_advice
from recommendations.recommender_engine import get_recommendations
from recommendations.models import Product


# Initialize pipelines (models loaded lazily)
pipeline = FaceAnalysisPipeline()
yolo_pipeline = YOLOAnalysisPipeline()


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

                # Run unified pipeline: MediaPipe → YOLO → MobileNet
                raw = unified_analyze(image_bytes)

                if raw.get("status") == "no_face":
                    error = raw.get("error", "No face detected.")
                    analysis_result = None
                elif raw.get("status") == "error":
                    error = raw.get("error", "Analysis failed.")
                    analysis_result = None
                else:
                    # Normalise unified result into the shape the rest of the view expects
                    analysis_result = {
                        "skin_type":    raw.get("mobilenet", {}).get("skin_type", {}),
                        "skin_concerns":raw.get("mobilenet", {}).get("skin_concerns", {}),
                        "image_base64": raw.get("image_base64"),
                        "face_bbox":    raw.get("face_bbox"),
                        # YOLO detections for bounding box overlay
                        "yolo_detections": raw.get("yolo", {}).get("detections", []),
                        "yolo_severity":   raw.get("yolo", {}).get("severity", "None"),
                    }

                # If models are missing or pipeline failed, show error only and skip results dashboard
                if analysis_result and analysis_result.get("error"):
                    error = analysis_result.get("error")
                    analysis_result = None
                else:
                    # Fetch Recommendations
                    if analysis_result:
                        skin_type_preds = analysis_result.get("skin_type", {}).get("predictions", [])
                        skin_type = skin_type_preds[0]["class"] if skin_type_preds else "Normal"
                        analysis_result["skin_type_label"] = skin_type
                        print(f"✓ Skin Type: {skin_type}")

                        CONFIDENCE_THRESHOLD = 0.3  # 30% (better chance for valid concerns to appear)

                        concerns_preds = analysis_result.get("skin_concerns", {}).get("predictions", [])
                        print(f"✓ Skin Concerns Predictions: {len(concerns_preds)} predictions received")

                        final_concerns = []  # Initialize default value
                        main_concern = None

                        if not concerns_preds:
                            print("⚠ WARNING: No skin concerns predictions received — falling back to YOLO detections.")

                            # Build concerns from YOLO detections instead
                            yolo_dets = analysis_result.get("yolo_detections", [])
                            yolo_concern_map: dict[str, int] = {}
                            for det in yolo_dets:
                                lbl = det["label"].lower().replace("_", "").replace(" ", "")
                                # Use highest confidence per label
                                conf = int(det["confidence"] * 100)
                                if lbl not in yolo_concern_map or conf > yolo_concern_map[lbl]:
                                    yolo_concern_map[lbl] = conf

                            if yolo_concern_map:
                                sorted_concerns = sorted(
                                    [{"name": k, "confidence": v} for k, v in yolo_concern_map.items()],
                                    key=lambda x: x["confidence"], reverse=True
                                )
                                for c in sorted_concerns:
                                    c["explanation"] = generate_skin_explanation(c["name"], c["confidence"])
                                    c["ingredient_advice"] = get_ingredient_advice(c["name"])
                                main_concern = sorted_concerns[0]["name"]
                                concerns_list = [c["name"] for c in sorted_concerns]
                                analysis_result["all_detected_concerns"] = sorted_concerns
                                analysis_result["detected_concerns"] = concerns_list
                                final_concerns = concerns_list
                            else:
                                analysis_result["flags"] = {
                                    "acne": False, "wrinkles": False, "pores": False,
                                    "darkspots": False, "blackheads": False,
                                }
                                analysis_result["detected_concerns"] = []
                                analysis_result["all_detected_concerns"] = []
                        else:
                            detected_concerns_with_confidence = [
                                {
                                    "name": p["class"].lower().replace("_", ""),
                                    "confidence": int(p["confidence"] * 100)  # Convert to 0-100 scale
                                }
                                for p in concerns_preds
                                if p["confidence"] >= CONFIDENCE_THRESHOLD
                            ]

                            concerns_list = [c["name"] for c in detected_concerns_with_confidence]
                            print(f"✓ Detected Concerns (>{CONFIDENCE_THRESHOLD}): {concerns_list}")

                            if detected_concerns_with_confidence:
                                sorted_concerns = sorted(detected_concerns_with_confidence, key=lambda x: x["confidence"], reverse=True)
                                main_concern = sorted_concerns[0]["name"]
                                # Attach AI explanation to each concern
                                for c in sorted_concerns:
                                    c["explanation"] = generate_skin_explanation(
                                        c["name"], c["confidence"]
                                    )
                                    c["ingredient_advice"] = get_ingredient_advice(c["name"])
                                analysis_result["all_detected_concerns"] = sorted_concerns
                            else:
                                main_concern = None
                                analysis_result["all_detected_concerns"] = []

                            analysis_result["detected_concerns"] = [main_concern] if main_concern else []

                            # Create flags for the template to handle dynamic icons/badges (visual feedback for all)
                            analysis_result["flags"] = {
                                "acne": "acne" in concerns_list,
                                "wrinkles": "wrinkles" in concerns_list,
                                "pores": "pores" in concerns_list or "texture" in concerns_list,
                                "darkspots": "darkspots" in concerns_list or "dark_spots" in concerns_list or "spots" in concerns_list,
                                "blackheads": "blackheads" in concerns_list,
                            }

                            # Use all detected concerns for recommendations
                            final_concerns = concerns_list if concerns_list else []
                            analysis_result["detected_concerns"] = final_concerns

                        query = {
                            "skin_type": skin_type,
                            "concerns": final_concerns,
                            "allergies": [a.strip() for a in request.POST.get("allergies", "").split(",") if a.strip()],
                        }

                        # Use TF-IDF based recommendations with active ingredients and allergy warnings
                        recommended_products = get_recommendations(query, top_k=50)

                        # Normalise scores to 0–100 relative to the top scorer in this batch
                        raw_scores = [p.get("score", 0) for p in recommended_products]
                        max_score  = max(raw_scores) if raw_scores else 1
                        min_score  = min(raw_scores) if raw_scores else 0
                        score_range = max_score - min_score if max_score != min_score else 1

                        for p in recommended_products:
                            raw = p.get("score", 0)
                            # Scale so top product = ~95%, others spread below it
                            normalised = 55 + round(((raw - min_score) / score_range) * 40)
                            p["match_score"] = max(55, min(95, normalised))

                            # Build specific human-readable reason
                            concerns_matched = [c for c in (p.get("concern") or []) if c]
                            p_type = (p.get("type") or "product").lower()

                            reasons = []

                            # Concern alignment
                            if concerns_matched and final_concerns:
                                shared = [c for c in concerns_matched
                                          if any(fc.lower() in c.lower() or c.lower() in fc.lower()
                                                 for fc in final_concerns)]
                                if shared:
                                    reasons.append(f"Addresses {', '.join(shared[:2])}")
                                else:
                                    reasons.append(f"Targets {', '.join(concerns_matched[:2])}")

                            # Skin type alignment
                            if skin_type and skin_type != "Normal":
                                reasons.append(f"suited for {skin_type} skin")

                            # Score tier label
                            score_pct = p["match_score"]
                            if score_pct >= 88:
                                tier = "Strong match"
                            elif score_pct >= 75:
                                tier = "Good match"
                            else:
                                tier = "Relevant pick"

                            if reasons:
                                p["match_reason"] = f"{tier} — {'; '.join(reasons)}."
                            else:
                                p["match_reason"] = f"{tier} for your skin profile."

                        # Fetch Product objects from DB to get IDs and synchronized data
                        product_urls = [p.get('link') for p in recommended_products if p.get('link')]
                        product_names = [p.get('name') for p in recommended_products if p.get('name')]
                        
                        db_products_by_url = {p.product_url: p for p in Product.objects.filter(product_url__in=product_urls)}
                        db_products_by_name = {p.name: p for p in Product.objects.filter(name__in=product_names)}

                        # Update recommended products with database info
                        for p in recommended_products:
                            url = p.get('link')
                            name = p.get('name')
                            db_prod = db_products_by_url.get(url) or db_products_by_name.get(name)
                            
                            if db_prod:
                                p['id'] = db_prod.id
                                # Prefer DB image and brand if available
                                if db_prod.image_url:
                                    p['image_url'] = db_prod.image_url
                                if db_prod.brand:
                                    p['brand'] = db_prod.brand

                        # Build a personalized routine based on detected skin type and concerns
                        try:
                            routine = build_routine({
                                "skin_type": skin_type,
                                "skin_concerns": final_concerns or [],
                            })
                        except Exception as e:
                            routine = None
                            print(f"⚠ Warning: Routine generation failed: {e}")

                        print(f"Main concern: {main_concern}. Found {len(recommended_products)} products for {skin_type}.")

                # DEBUG OUTPUT 
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


def realtime(request):
    """Render the real-time webcam skin concern detection page."""
    return render(request, "face_analysis/realtime.html")


@csrf_exempt
@require_POST
def realtime_analyze(request):
    """
    Accept a base64-encoded webcam frame, run the CNN pipeline,
    and return JSON with skin type + concern predictions.
    """
    try:
        body = json.loads(request.body)
        frame_b64 = body.get("frame", "")

        # Decode base64 → numpy BGR image
        header, _, data = frame_b64.partition(",")
        img_bytes = base64.b64decode(data if data else frame_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame_bgr is None:
            return JsonResponse({"error": "Could not decode frame"}, status=400)

        result = pipeline.analyze(frame_bgr)

        if result.get("error"):
            return JsonResponse({"error": result["error"]})

        CONFIDENCE_THRESHOLD = 0.30

        # Skin type
        skin_type_preds = result.get("skin_type", {}).get("predictions", [])
        skin_type = skin_type_preds[0]["class"] if skin_type_preds else None

        # Skin concerns
        concerns_preds = result.get("skin_concerns", {}).get("predictions", [])
        detected = [
            {"name": p["class"], "confidence": round(p["confidence"] * 100)}
            for p in concerns_preds
            if p["confidence"] >= CONFIDENCE_THRESHOLD
        ]
        detected.sort(key=lambda x: x["confidence"], reverse=True)

        # Face bounding box (relative coords for overlay)
        face_bbox = result.get("face_bbox")

        return JsonResponse({
            "skin_type": skin_type,
            "concerns": detected,
            "face_bbox": face_bbox,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def realtime_yolo_analyze(request):
    """
    Accept a base64-encoded webcam frame, run YOLO-only detection (no MobileNet)
    for fast real-time response. Returns boxes + labels for canvas overlay.
    """
    print("REALTIME YOLO CALLED")
    try:
        body = json.loads(request.body)
        frame_b64 = body.get("frame", "")

        # Strip the data URI prefix if present (e.g. "data:image/jpeg;base64,...")
        if "," in frame_b64:
            frame_b64 = frame_b64.split(",", 1)[1]

        img_bytes = base64.b64decode(frame_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame_bgr is None:
            return JsonResponse({"error": "Could not decode frame"}, status=400)

        print(f"[YOLO] Frame shape: {frame_bgr.shape}")

        result = yolo_pipeline.detect_only(frame_bgr)
        print(f"[YOLO] Status: {result.get('status')} | Face bbox: {result.get('face_bbox')} | Detections: {len(result.get('detections', []))}")
        return JsonResponse(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


def yolo_index(request):
    """Page for YOLO + MobileNet image upload analysis."""
    return render(request, "face_analysis/yolo_index.html")


@csrf_exempt
@require_POST
def yolo_analyze(request):
    """
    Accepts a multipart image upload OR base64 JSON body.
    Runs the full unified pipeline: MediaPipe → YOLO → MobileNet.
    """
    print("FULL ANALYSIS CALLED")
    try:
        if request.FILES.get("image"):
            image_bytes = request.FILES["image"].read()
        else:
            body = json.loads(request.body)
            frame_b64 = body.get("frame", "")
            _, _, data = frame_b64.partition(",")
            image_bytes = base64.b64decode(data if data else frame_b64)

        result = unified_analyze(image_bytes)
        return JsonResponse(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
