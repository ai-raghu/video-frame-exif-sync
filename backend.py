from flask import Flask, request, send_file, jsonify
import subprocess
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Function to extract a frame from a video
def extract_frame(video_path):
    output_frame = os.path.join(app.config['UPLOAD_FOLDER'], "extracted_frame.jpg")

    # Check if FFmpeg is installed
    ffmpeg_check = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    print("FFmpeg Check:", ffmpeg_check.stdout)

    # Adjusting FFmpeg command to support HEVC (H.265)
    command = [
        "ffmpeg", "-i", video_path, "-vf", "yadif,select=eq(n\\,10)", "-vsync", "vfr",
        "-frames:v", "1", "-pix_fmt", "yuvj420p", "-q:v", "2", output_frame
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print("FFmpeg Output:", result.stdout)
    print("FFmpeg Error:", result.stderr)

    if os.path.exists(output_frame):
        print(f"✅ Frame extracted successfully: {output_frame}")
    else:
        print("❌ Error: Frame extraction failed.")

    return output_frame if os.path.exists(output_frame) else None

# Function to sync EXIF metadata
def sync_exif(reference_photo, target_photo):
    command = ["exiftool", "-TagsFromFile", reference_photo, "-all:all", "-overwrite_original", target_photo]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Log the embedded metadata
    metadata_command = ["exiftool", target_photo]
    metadata_output = subprocess.run(metadata_command, capture_output=True, text=True).stdout
    print("🔍 Embedded Metadata:")
    print(metadata_output)
    
    return target_photo

@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files or 'photo' not in request.files:
        return jsonify({"error": "Missing file uploads"}), 400
    
    video = request.files['video']
    photo = request.files['photo']
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(video.filename))
    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(photo.filename))
    
    video.save(video_path)
    photo.save(photo_path)
    
    extracted_frame = extract_frame(video_path)
    if not extracted_frame:
        return jsonify({"error": "Failed to extract frame"}), 500
    
    final_image = sync_exif(photo_path, extracted_frame)
    return send_file(final_image, as_attachment=True)

@app.route('/')
def home():
    return "✅ API is running. Use the frontend to upload files."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
