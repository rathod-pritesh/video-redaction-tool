# VideoRedact

** VideoRedact ** is a simple AI powered video redaction tool that helps remove sensitive content from videos before sharing them.

It automatically detects people and selected objects in video frames and applies blur and redaction to protect privacy. The processed video is converted into a browser friendly format and temporarily stored in Amazon S3 for preview and download.

# Features
Automatically detects people, cars, motorcycles, buses, and trucks
Blurs detected sensitive objects in video frames
Adds redaction bounding boxes with detection confidence
Supports MP4, WebM, MOV, AVI, and MKV videos
Supports videos up to 100 MB
Provides a preview of the processed video
Downloads the processed video through a temporary S3 link
Uses temporary storage during video processing
Automatically removes temporary local processing files
No account is required to use the application

# How It Works
Upload a video through the web interface.
The AI model processes the video frame by frame.
Detected objects are blurred and redacted.
FFmpeg converts the processed video into a browser compatible H.264 MP4 format.
The processed video is temporarily uploaded to Amazon S3.
A temporary download and preview link is generated.
Local processing files are removed.

# Tech Stack
Python
Flask
OpenCV
Ultralytics YOLO
FFmpeg
Amazon S3
HTML
CSS
JavaScript
Bootstrap

# Project Structure

```
Video Redact/
├── app.py
├── requirements.txt
├── yolo26n.pt
├── services/
│   └── video_processor.py
├── static/
│   ├── css/
│   ├── js/
│   ├── favicon.png
│   └── videoreadact_logo.png
└── templates/
    ├── index.html
    └── toast.html
```

# Local Setup

Clone the repository and open the project directory:

```
git clone https://github.com/rathod-pritesh/video-redaction-tool.git
cd video-redaction-tool
```

Create and activate a virtual environment:

```
python -m venv .venv
```

Windows:

```
.venv\Scripts\activate
```

Install the dependencies:

```
pip install -r requirements.txt
```

Make sure FFmpeg is installed and available in your system PATH.

Create a .env file in the project root:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_bucket_name
```

Start the application:

```
python app.py
```

Then open:

```
http://127.0.0.1:5000
```

# Important

Never commit your .env file or expose your AWS credentials.

The application uses temporary local storage while processing videos. The final processed video is uploaded to Amazon S3 and accessed through a temporary presigned URL.

Testing Videos

TEST_VIDEOS.md contains the sources used for testing the application.

License

This project is intended for learning, development, and portfolio purposes. Add a specific open source license if you plan to allow others to reuse or distribute the code.