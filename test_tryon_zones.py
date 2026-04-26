"""
Test script for the try-on zones feature.
"""
import cv2
from recommendations.skincare_zones import apply_skincare_zones

def test_zones():
    """Test the skincare zones on a sample image."""
    # Read a test image
    test_image_path = "debug_face.jpg"  # Using existing debug image
    
    try:
        with open(test_image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Test different categories
        categories = [
            "eye care",
            "moisturizer",
            "serum",
            "sunscreen",
            "acne treatment"
        ]
        
        for category in categories:
            print(f"\nTesting category: {category}")
            result = apply_skincare_zones(image_bytes, category)
            
            if "error" in result:
                print(f"  ❌ Error: {result['error']}")
            else:
                print(f"  ✓ Success! Found {len(result['zones'])} zones")
                for zone in result['zones']:
                    print(f"    - {zone['label']}: {len(zone['points'])} points")
        
        print("\n✓ All tests completed!")
        
    except FileNotFoundError:
        print(f"❌ Test image not found: {test_image_path}")
        print("Please ensure you have a face image for testing.")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_zones()
