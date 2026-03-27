import os
import base64
import tempfile
import re
import io
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from PIL import Image

# ==========================================
# ULTRA-STRICT CPU CORE OPTIMIZATION
# Forces AI to sip CPU slowly rather than spike
# ==========================================
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_THREAD_LIMIT"] = "1"

from rembg import remove, new_session
import vtracer

app = Flask(__name__)
CORS(app)

# ==========================================
# LAZY LOADING THE AI MODEL
# Prevents 502 Bad Gateway timeouts on server startup
# ==========================================
_session = None

def get_session():
    global _session
    if _session is None:
        print("[AI Engine] Loading AI Background Removal Model into memory...")
        _session = new_session("u2net")
    return _session

@app.route('/')
def index():
    # Serves the beautiful Premium V4.2 Frontend UI
    return render_template('index.html')

# ==========================================
# PWA ROUTES (Progressive Web App)
# Serves the manifest and service worker from the root URL
# ==========================================
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/api/process-image', methods=['POST'])
def process_image():
    if 'file' not in request.files:
        return jsonify({'detail': 'No file part'}), 400
        
    file = request.files['file']
    
    if file.filename == '' or not file.filename.lower().endswith('.png'):
        return jsonify({'detail': 'Only .png files are supported'}), 400

    temp_png_path = None
    temp_svg_path = None

    try:
        print(f"\n[AI Engine] New Request: Processing {file.filename}")

        # --- MEMORY PROTECTION: Strict 1024px Downscaling ---
        img = Image.open(file.stream).convert("RGBA")
        max_dimension = 1024 
        
        if img.width > max_dimension or img.height > max_dimension:
            print(f"[AI Engine] Image is {img.width}x{img.height}. Downscaling to {max_dimension}px safely...")
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        
        # Convert safely resized image back to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        safe_input_bytes = img_byte_arr.getvalue()

        # --- 1. PERFECT CUT ---
        print("[AI Engine] Extracting foreground (Alpha Matting)...")
        bg_removed_data = remove(
            safe_input_bytes,
            session=get_session(), # Calls the lazy-loaded model
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=5
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_png:
            temp_png.write(bg_removed_data)
            temp_png_path = temp_png.name

        temp_svg_path = temp_png_path + ".svg"

        # --- 2. CLEAN SVG VECTORIZATION ---
        print("[AI Engine] Tracing Spline Vectors...")
        vtracer.convert_image_to_svg_py(
            temp_png_path,
            temp_svg_path,
            colormode='color',
            hierarchical='stacked',
            mode='spline',
            filter_speckle=10,     
            color_precision=8,     
            layer_difference=16,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=10,
            splice_threshold=45,
            path_precision=3
        )

        # --- 3. FORMAT XML & SCRUB WHITE BACKGROUNDS ---
        with open(temp_svg_path, "r") as svg_file:
            svg_content = svg_file.read()

        # Scrub any rogue background paths to guarantee SVG transparency
        svg_content = re.sub(r'<path[^>]*fill=["\']?(?:rgb\(\s*255\s*,\s*255\s*,\s*255\s*\)|#ffffff|#fff)["\']?[^>]*\/?>(?:<\/path>)?', '', svg_content, flags=re.IGNORECASE)
        
        if not svg_content.strip().startswith("<?xml"):
            svg_content = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n\n' + svg_content

        png_base64 = base64.b64encode(bg_removed_data).decode('utf-8')
        
        print("[AI Engine] ✅ Successfully generated PNG & SVG!")

        return jsonify({
            "status": "success",
            "png_base64": f"data:image/png;base64,{png_base64}",
            "svg_content": svg_content
        })

    except Exception as e:
        print(f"[CRITICAL ERROR] {str(e)}")
        return jsonify({'detail': str(e)}), 500

    finally:
        # GUARANTEED CLEANUP to prevent disk space exhaustion
        if temp_png_path and os.path.exists(temp_png_path):
            os.remove(temp_png_path)
        if temp_svg_path and os.path.exists(temp_svg_path):
            os.remove(temp_svg_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)