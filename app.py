import os
import uuid
import tempfile
import shutil
import boto3
import subprocess

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from services.video_processor import process_video

load_dotenv()

s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

app = Flask(__name__)

TEMP_BASE_DIR = os.path.join(tempfile.gettempdir(), "videoredact_processing")
os.makedirs(TEMP_BASE_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "mp4",
    "webm",
    "mov",
    "avi",
    "mkv",
}

MAX_FILE_SIZE = 100 * 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "success": False,
        "error": "The uploaded video exceeds the 100MB size limit."
    }), 413


@app.route("/")
def index():
    return render_template("index.html")


def convert_to_browser_video(input_path, output_path):
    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        output_path,
    ]
    
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg conversion failed: {result.stderr}"
        )


@app.route("/video/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({
            "success": False,
            "error": "No video file was uploaded."
        }), 400

    video = request.files["video"]

    if not video or video.filename == "":
        return jsonify({
            "success": False,
            "error": "No video file was selected."
        }), 400

    if not allowed_file(video.filename):
        return jsonify({
            "success": False,
            "error": "Unsupported video format. Allowed formats: MP4, WebM, MOV, AVI, MKV."
        }), 400

    original_name = secure_filename(video.filename)
    file_extension = os.path.splitext(original_name)[1].lower() or ".mp4"
    unique_id = uuid.uuid4().hex

    input_filename = f"{unique_id}{file_extension}"
    output_filename = f"{unique_id}_redacted.mp4"
    browser_output_filename = f"{unique_id}_redacted_h264.mp4"

    temp_dir = tempfile.mkdtemp(prefix="vr_task_", dir=TEMP_BASE_DIR)
    input_path = os.path.join(temp_dir, input_filename)
    output_path = os.path.join(temp_dir, output_filename)
    
    browser_output_path = os.path.join(
        temp_dir,
        browser_output_filename
    )
    
    s3_key = None

    try:
        video.save(input_path)

        process_video(input_path, output_path)
        
        convert_to_browser_video(
            output_path,
            browser_output_path
        )
        
        s3_key = f"processed/{browser_output_filename}"
        
        s3.upload_file(
            browser_output_path,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                "ContentType": "video/mp4"
            }
        )
        
        processed_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": S3_BUCKET_NAME,
                "Key": s3_key
            },
            ExpiresIn=3600
        )
        
        if os.path.exists(input_path):
            os.remove(input_path)
            
        if os.path.exists(output_path):
            os.remove(output_path)
            
        if os.path.exists(browser_output_path):
            os.remove(browser_output_path)
            
        shutil.rmtree(temp_dir, ignore_errors=True)
            
        return jsonify({
            "success": True,
            "message": "Video processed successfully",
            "video": {
                "filename": os.path.basename(s3_key),
                "url": processed_url
            }
        })
        
       
    except Exception as error:
        app.logger.exception("Video processing failed")

        if s3_key:
            try:
                s3.delete_object(
                    Bucket=S3_BUCKET_NAME,
                    Key=s3_key
                )
            except Exception:
                app.logger.exception("Failed to clean S3 object")

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        return jsonify({
            "success": False,
            "error": "Video processing failed. Please check the video file and try again."
        }), 500


# @app.route("/video/processed/<filename>")
# def processed_video(filename):
 
#     safe_filename = secure_filename(filename)
#     task_id = request.args.get("task_id")

#     if task_id:
#         safe_task_id = secure_filename(task_id)
#         task_dir = os.path.join(TEMP_BASE_DIR, safe_task_id)
#         if os.path.exists(os.path.join(task_dir, safe_filename)):
#             return send_from_directory(task_dir, safe_filename, as_attachment=False)

#     if os.path.exists(TEMP_BASE_DIR):
#         for sub in os.listdir(TEMP_BASE_DIR):
#             candidate_dir = os.path.join(TEMP_BASE_DIR, sub)
#             if os.path.isdir(candidate_dir) and os.path.exists(os.path.join(candidate_dir, safe_filename)):
#                 return send_from_directory(candidate_dir, safe_filename, as_attachment=False)

#     return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    app.run(debug=False)