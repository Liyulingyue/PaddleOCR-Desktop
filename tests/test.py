import requests
import os
from PIL import Image, ImageDraw, ImageFont

# 创建测试图像
def create_test_image():
    img = Image.new('RGB', (200, 100), color='white')
    draw = ImageDraw.Draw(img)
    # 使用默认字体
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    draw.text((10, 30), "Hello OCR", fill='black', font=font)
    img.save('test.png')
    print("Test image created: test.png")

create_test_image()

# 测试健康检查
print("Testing health endpoint...")
try:
    response = requests.get('http://localhost:3000/health', timeout=5)
    if response.status_code == 200:
        print("Health check passed:", response.json())
    else:
        print("Health check failed with status:", response.status_code)
except Exception as e:
    print("Health check error:", e)

# 测试OCR API
print("Testing OCR endpoint...")
test_image_path = os.path.join(os.path.dirname(__file__), 'test.png')
if os.path.exists(test_image_path):
    try:
        with open(test_image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post('http://localhost:3000/ocr', files=files, timeout=30)
            if response.status_code == 200:
                print("OCR test passed:", response.json())
            else:
                print("OCR test failed with status:", response.status_code, response.text)
    except Exception as e:
        print("OCR test error:", e)
else:
    print("Test image 'test.png' not found.")