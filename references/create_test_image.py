#!/usr/bin/env python3
"""
Generate a test image for PP-Structure-V3 ONNX testing
"""

import cv2
import numpy as np

def create_test_image():
    """Create a simple test image with text and table-like structure"""
    # Create white background
    img = np.ones((600, 800, 3), dtype=np.uint8) * 255

    # Add some mock text areas (black rectangles)
    cv2.rectangle(img, (50, 50), (350, 120), (0, 0, 0), -1)  # Text area
    cv2.rectangle(img, (50, 200), (350, 350), (0, 0, 0), -1)  # Table area
    cv2.rectangle(img, (50, 400), (350, 470), (0, 0, 0), -1)  # Another text area

    # Add some text labels
    cv2.putText(img, "Test Document", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(img, "Table Area", (60, 230), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(img, "Formula: E=mc^2", (60, 430), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return img

if __name__ == '__main__':
    test_img = create_test_image()
    cv2.imwrite('test_document.jpg', test_img)
    print("Test image saved as test_document.jpg")