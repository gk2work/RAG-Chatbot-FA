# upload_routes.py
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os
import uuid
from datetime import datetime
from PIL import Image
import io
import logging


upload_bp = Blueprint('upload', __name__)
logger = logging.getLogger(__name__)

# Configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg', 'ico'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB for logos
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'logos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'favicons'), exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_file(file: FileStorage):
    """Validate uploaded image file"""
    if not file or not file.filename:
        return False, "No file provided"
    
    if not allowed_file(file.filename):
        return False, "File type not allowed. Only PNG, JPG, SVG, and ICO files are supported"
    
    if len(file.read()) > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.1f}MB"
    
    # Reset file pointer
    file.seek(0)
    return True, "Valid file"

def generate_unique_filename(original_filename):
    """Generate unique filename to prevent conflicts"""
    file_extension = secure_filename(original_filename).rsplit('.', 1)[1].lower()
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{timestamp}_{unique_id}.{file_extension}"

def process_image(file: FileStorage, max_width=800, max_height=600):
    """Process and optimize image file"""
    try:
        # Skip processing for SVG files
        if file.filename.lower().endswith('.svg'):
            return file.read()
        
        # Open image with PIL
        image = Image.open(file.stream)
        
        # Convert RGBA to RGB if necessary (for JPEG)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Resize if too large
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        format_map = {'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG', 'ico': 'ICO'}
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        save_format = format_map.get(file_ext, 'PNG')
        
        if save_format == 'JPEG':
            image.save(output, format=save_format, quality=85, optimize=True)
        else:
            image.save(output, format=save_format, optimize=True)
        
        output.seek(0)
        return output.read()
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        # Return original file content if processing fails
        file.seek(0)
        return file.read()

@upload_bp.route('/logo', methods=['POST'])
def upload_logo():
    """Upload and process logo file"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        folder = request.form.get('folder', 'logos')
        
        # Validate file
        is_valid, error_message = validate_image_file(file)
        if not is_valid:
            return jsonify({"success": False, "error": error_message}), 400
        
        # Generate unique filename
        filename = generate_unique_filename(file.filename)
        
        # Process image
        processed_image_data = process_image(file)
        
        # Save file
        folder_path = os.path.join(UPLOAD_FOLDER, folder)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, filename)
        
        with open(file_path, 'wb') as f:
            f.write(processed_image_data)
        
        # Generate URL (in production, this would be a CDN URL)
        file_url = f"/uploads/{folder}/{filename}"
        
        logger.info(f"Successfully uploaded file: {filename}")
        
        return jsonify({
            "success": True,
            "url": file_url,
            "filename": filename,
            "size": len(processed_image_data),
            "message": "File uploaded successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Upload failed. Please try again."
        }), 500

@upload_bp.route('/favicon', methods=['POST'])
def upload_favicon():
    """Upload favicon (smaller size limits)"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        
        # Validate file
        is_valid, error_message = validate_image_file(file)
        if not is_valid:
            return jsonify({"success": False, "error": error_message}), 400
        
        # Generate unique filename
        filename = generate_unique_filename(file.filename)
        
        # Process image (smaller size for favicon)
        processed_image_data = process_image(file, max_width=64, max_height=64)
        
        # Save file
        folder_path = os.path.join(UPLOAD_FOLDER, 'favicons')
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, filename)
        
        with open(file_path, 'wb') as f:
            f.write(processed_image_data)
        
        # Generate URL
        file_url = f"/uploads/favicons/{filename}"
        
        logger.info(f"Successfully uploaded favicon: {filename}")
        
        return jsonify({
            "success": True,
            "url": file_url,
            "filename": filename,
            "size": len(processed_image_data),
            "message": "Favicon uploaded successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Favicon upload error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Favicon upload failed. Please try again."
        }), 500