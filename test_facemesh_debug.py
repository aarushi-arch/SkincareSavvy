import cv2
import sys

from face_analysis.services.cnn import FaceAnalysisPipeline, draw_landmarks_debug


def main(image_path: str = "test_selfie.jpg"):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to load image: {image_path}")
        sys.exit(1)

    pipeline = FaceAnalysisPipeline()

    # Convert to RGB for MediaPipe
    image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if pipeline.face_mesh is None:
        print("FaceMesh not initialized in pipeline (face_mesh is None)")
        sys.exit(1)

    results = pipeline.face_mesh.process(image_rgb)

    if not results or not results.multi_face_landmarks:
        print("❌ No landmarks detected")
        sys.exit(0)

    face_landmarks = results.multi_face_landmarks[0]
    debug_img = draw_landmarks_debug(img.copy(), face_landmarks)
    out_path = "landmarks_debug.jpg"
    cv2.imwrite(out_path, debug_img)
    print(f"✅ Landmarks drawn and saved to {out_path}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("image", nargs="?", default="test_selfie.jpg")
    args = p.parse_args()
    main(args.image)
