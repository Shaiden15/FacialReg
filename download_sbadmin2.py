import os
import zipfile
import requests
from pathlib import Path

def download_and_extract():
    # Create necessary directories
    static_dir = Path("app/student_attendance_system/static")
    vendor_dir = static_dir / "vendor"
    css_dir = static_dir / "css"
    js_dir = static_dir / "js"
    img_dir = static_dir / "img"
    
    for d in [vendor_dir, css_dir, js_dir, img_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Download SB Admin 2
    print("Downloading SB Admin 2 template...")
    url = "https://github.com/StartBootstrap/startbootstrap-sb-admin-2/archive/refs/tags/v4.1.4.zip"
    response = requests.get(url, stream=True)
    zip_path = "sb-admin-2.zip"
    
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=128):
            f.write(chunk)
    
    # Extract files
    print("Extracting files...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(".")
    
    # Copy required files
    source_dir = "startbootstrap-sb-admin-2-4.1.4"
    
    # Copy CSS
    (Path(source_dir) / "css").replace(css_dir / "sb-admin-2.min.css")
    
    # Copy JS
    (Path(source_dir) / "js").replace(js_dir / "sb-admin-2.min.js")
    (Path(source_dir) / "js").replace(js_dir / "demo")
    
    # Copy vendor files
    vendor_src = Path(source_dir) / "vendor"
    for item in vendor_src.iterdir():
        if item.is_dir():
            (vendor_src / item.name).replace(vendor_dir / item.name)
    
    # Copy images
    (Path(source_dir) / "img").replace(img_dir / "undraw_profile.svg")
    
    # Clean up
    os.remove(zip_path)
    import shutil
    shutil.rmtree(source_dir)
    
    print("SB Admin 2 template has been installed successfully!")

if __name__ == "__main__":
    download_and_extract()
