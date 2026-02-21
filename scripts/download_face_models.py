import os
import requests
from pathlib import Path

def download_file(url, path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

def main():
    # Create models directory if it doesn't exist
    models_dir = Path("app/student_attendance_system/static/models")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # List of model files to download
    base_url = "https://github.com/justadudewhohacks/face-api.js/raw/master/weights"
    model_files = [
        "tiny_face_detector_model-weights_manifest.json",
        "tiny_face_detector_model-shard1",
        "face_landmark_68_model-weights_manifest.json",
        "face_landmark_68_model-shard1",
        "face_recognition_model-weights_manifest.json",
        "face_recognition_model-shard1",
        "face_recognition_model-shard2"
    ]
    
    # Download each file
    for file in model_files:
        url = f"{base_url}/{file}"
        path = models_dir / file
        print(f"Downloading {file}...")
        try:
            download_file(url, path)
            print(f"Successfully downloaded {file}")
        except Exception as e:
            print(f"Error downloading {file}: {e}")

if __name__ == "__main__":
    main()
