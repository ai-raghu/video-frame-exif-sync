from flask import Flask, request, send_file, jsonify
import subprocess
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Define upload folder
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Function to extract a frame from a video (Handles HEVC, HDR issues)
def extract_frame(video_path):
    output_frame = os.path.join(app.config['UPLOAD_FOLDER'], "extracted_frame.jpg")

    # Log FFmpeg version
    ffmpeg_check = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    print("FFmpeg Version:", ffmpeg_check.stdout)

    # Optimized FFmpeg command
    command = [
        "ffmpeg", "-y", "-i", video_path, 
        "-map", "0:v:0",  # Ensure we only process the first video stream
        "-pix_fmt", "yuv420p",  # Convert HDR 10-bit to standard 8-bit
        "-vf", "scale=1920:1080:flags=lanczos",  # Scale and maintain quality
        "-c:v", "mjpeg", "-q:v", "2",
        "-frames:v", "1", output_frame
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Debugging logs
    print("FFmpeg Output:", result.stdout.decode())
    print("FFmpeg Error:", result.stderr.decode())

    if os.path.exists(output_frame):
        print(f"✅ Frame extracted successfully: {output_frame}")
        return output_frame
    else:
        print("❌ Error: Frame extraction failed.")
        return None

# Function to sync EXIF metadata
def sync_exif(reference_photo, target_photo):
    command = ["exiftool", "-TagsFromFile", reference_photo, "-all:all", "-overwrite_original", target_photo]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Retrieve and log metadata
    metadata_command = ["exiftool", target_photo]
    metadata_output = subprocess.run(metadata_command, capture_output=True, text=True).stdout
    print("✅ Embedded Metadata:")
    print(metadata_output)

    return target_photo

# API route for file upload & processing
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
    
    # Extract frame from video
    extracted_frame = extract_frame(video_path)
    if not extracted_frame:
        return jsonify({"error": "Failed to extract frame"}), 500
    
    # Sync EXIF metadata
    final_image = sync_exif(photo_path, extracted_frame)
    
    return send_file(final_image, as_attachment=True)

# Health check route
@app.route('/')
def home():
    return "✅ API is running. Use the frontend to upload files."

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
