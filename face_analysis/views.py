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
                    raw_dets = raw.get("yolo", {}).get("detections", [])
                    for d in raw_dets:
                        d["confidence_pct"] = round(d.get("confidence", 0) * 100)

                    analysis_result = {
                        "skin_type":    raw.get("mobilenet", {}).get("skin_type", {}),
                        "skin_concerns":raw.get("mobilenet", {}).get("skin_concerns", {}),
                        "image_base64": raw.get("image_base64"),
                        "face_bbox":    raw.get("face_bbox"),
                        "yolo_detections": [d for d in raw_dets if d["confidence_pct"] >= 10],
                        "yolo_severity":   raw.get("yolo", {}).get("severity", "None"),
                    }
                    # Store image in session for the Try-On feature
                    if raw.get("image_base64"):
                        request.session["last_analysis_image"] = raw["image_base64"]
                    
                    # Store skin type in session for concern-based recommendations
                    skin_type_preds = analysis_result.get("skin_type", {}).get("predictions", [])
                    skin_type = skin_type_preds[0]["class"] if skin_type_preds else "Normal"
                    request.session["detected_skin_type"] = skin_type

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

                        CONFIDENCE_THRESHOLD = 0.35  # 35% — balanced threshold for subtle concerns like wrinkles

                        concerns_preds = analysis_result.get("skin_concerns", {}).get("predictions", [])
                        no_concerns_flag = analysis_result.get("skin_concerns", {}).get("no_concerns", False)
                        print(f"✓ Skin Concerns Predictions: {len(concerns_preds)} received | no_concerns={no_concerns_flag}")

                        final_concerns = []
                        main_concern = None
                        all_concerns_for_selection = []  # NEW: Store all concerns for user selection

                        # Filter MobileNet predictions above threshold
                        high_conf_preds = [p for p in concerns_preds if p["confidence"] >= CONFIDENCE_THRESHOLD]

                        if no_concerns_flag:
                            # YOLO found nothing above gate — explicitly no concerns
                            analysis_result["all_detected_concerns"] = []
                            analysis_result["detected_concerns"] = []
                            analysis_result["flags"] = {
                                "acne": False, "wrinkles": False, "pores": False,
                                "darkspots": False, "blackheads": False,
                            }

                        elif not high_conf_preds:
                            # MobileNet has no high-confidence predictions — fall back to YOLO
                            print("⚠ MobileNet below threshold — falling back to YOLO detections.")

                            yolo_dets = analysis_result.get("yolo_detections", [])
                            yolo_concern_map: dict[str, int] = {}
                            for det in yolo_dets:
                                lbl = det["label"].lower().replace("_", "").replace(" ", "")
                                conf = det.get("confidence_pct", int(det.get("confidence", 0) * 100))
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
                                all_concerns_for_selection = sorted_concerns  # NEW
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
                                    "confidence": p.get("final_pct", int(p["confidence"] * 100))
                                }
                                for p in concerns_preds
                                if p["confidence"] >= CONFIDENCE_THRESHOLD
                            ]

                            concerns_list = [c["name"] for c in detected_concerns_with_confidence]
                            print(f"✓ Detected Concerns (>{CONFIDENCE_THRESHOLD}): {concerns_list}")
                            print(f"✓ Total MobileNet predictions: {len(concerns_preds)}")
                            print(f"✓ Predictions above threshold: {len(detected_concerns_with_confidence)}")

                            # If only one or no concerns above threshold, include top 3 predictions anyway
                            if len(detected_concerns_with_confidence) <= 1 and len(concerns_preds) > 1:
                                print(f"⚠ Only {len(detected_concerns_with_confidence)} concern(s) above threshold. Including top 3 predictions.")
                                all_predictions = [
                                    {
                                        "name": p["class"].lower().replace("_", ""),
                                        "confidence": p.get("final_pct", int(p["confidence"] * 100))
                                    }
                                    for p in concerns_preds
                                ]
                                # Sort by confidence and take top 3
                                sorted_all = sorted(all_predictions, key=lambda x: x["confidence"], reverse=True)
                                detected_concerns_with_confidence = sorted_all[:3]
                                concerns_list = [c["name"] for c in detected_concerns_with_confidence]
                                print(f"✓ Expanded to show top 3: {concerns_list}")

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
                                all_concerns_for_selection = sorted_concerns  # NEW
                            else:
                                main_concern = None
                                analysis_result["all_detected_concerns"] = []

                            analysis_result["detected_concerns"] = concerns_list if concerns_list else []

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
                        
                        # Store all concerns in session for later selection
                        request.session["all_detected_concerns"] = all_concerns_for_selection
                        request.session["default_concern"] = main_concern if main_concern else None

                        # DON'T generate recommendations here - wait for user to select a concern
                        # Recommendations will be loaded via AJAX when user clicks on a concern card
                        recommended_products = []
                        routine = None

                        print(f"✓ Analysis complete. Detected {len(all_concerns_for_selection)} concerns. Skin type: {skin_type}")
                        print(f"✓ All detected concerns: {[c['name'] for c in all_concerns_for_selection]}")
                        print(f"✓ analysis_result['all_detected_concerns']: {analysis_result.get('all_detected_concerns', [])}")

                # DEBUG OUTPUT 
                if analysis_result:
                    print(f"✓ Final analysis_result keys: {analysis_result.keys()}")
                    print(f"✓ Number of concerns in template data: {len(analysis_result.get('all_detected_concerns', []))}")

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


@csrf_exempt
@require_POST
def get_recommendations_for_concern(request):
    """
    Get product recommendations for a specific selected concern.
    """
    try:
        data = json.loads(request.body)
        selected_concern = data.get("concern")
        
        if not selected_concern:
            return JsonResponse({"error": "No concern specified"}, status=400)
        
        # Get stored data from session
        skin_type = request.session.get("detected_skin_type", "Normal")
        all_concerns = request.session.get("all_detected_concerns", [])
        
        # Verify the selected concern is valid
        valid_concerns = [c["name"] for c in all_concerns]
        if selected_concern not in valid_concerns:
            return JsonResponse({"error": "Invalid concern selected"}, status=400)
        
        # Get allergies if provided
        allergies = data.get("allergies", [])
        if isinstance(allergies, str):
            allergies = [a.strip() for a in allergies.split(",") if a.strip()]
        
        # Build query for recommendations
        query = {
            "skin_type": skin_type,
            "concerns": [selected_concern],  # Only the selected concern
            "allergies": allergies,
        }
        
        # Get recommendations
        recommended_products = get_recommendations(query, top_k=50)
        
        # Normalize scores
        raw_scores = [p.get("score", 0) for p in recommended_products]
        max_score = max(raw_scores) if raw_scores else 1
        min_score = min(raw_scores) if raw_scores else 0
        score_range = max_score - min_score if max_score != min_score else 1
        
        for p in recommended_products:
            raw = p.get("score", 0)
            normalised = 55 + round(((raw - min_score) / score_range) * 40)
            p["match_score"] = max(55, min(95, normalised))
            
            # Build match reason
            concerns_matched = [c for c in (p.get("concern") or []) if c]
            reasons = []
            
            if concerns_matched:
                if selected_concern.lower() in [c.lower() for c in concerns_matched]:
                    reasons.append(f"Targets {selected_concern}")
                else:
                    reasons.append(f"Addresses {', '.join(concerns_matched[:2])}")
            
            if skin_type and skin_type != "Normal":
                reasons.append(f"suited for {skin_type} skin")
            
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
        
        # Fetch Product objects from DB
        product_urls = [p.get('link') for p in recommended_products if p.get('link')]
        product_names = [p.get('name') for p in recommended_products if p.get('name')]
        
        db_products_by_url = {p.product_url: p for p in Product.objects.filter(product_url__in=product_urls)}
        db_products_by_name = {p.name: p for p in Product.objects.filter(name__in=product_names)}
        
        # Update with database info
        for p in recommended_products:
            url = p.get('link')
            name = p.get('name')
            db_prod = db_products_by_url.get(url) or db_products_by_name.get(name)
            
            if db_prod:
                p['id'] = db_prod.id
                if db_prod.image_url:
                    p['image_url'] = db_prod.image_url
                if db_prod.brand:
                    p['brand'] = db_prod.brand
                if db_prod.category:
                    p['category'] = db_prod.category
                if db_prod.rating:
                    p['rating'] = float(db_prod.rating)
        
        # Limit to top 50
        recommended_products = recommended_products[:50]
        
        return JsonResponse({
            "success": True,
            "concern": selected_concern,
            "skin_type": skin_type,
            "products": recommended_products,
            "count": len(recommended_products)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
