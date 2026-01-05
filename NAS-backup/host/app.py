from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = './backup'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 
    'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', '7z', 'csv',
    'json', 'xml', 'html', 'htm', 'js', 'css', 'py', 'java',
    'cpp', 'c', 'h', 'md', 'yml', 'yaml', 'ini', 'conf'
}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Flask configuration
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = os.urandom(24)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_unique_filename(filepath):
    """Generate a unique filename if file already exists (optional overwrite logic)"""
    # For overwriting, just return the original path
    # If you want to keep both, uncomment the code below:
    
    # if not os.path.exists(filepath):
    #     return filepath
    
    # # Add timestamp to filename
    # base, ext = os.path.splitext(filepath)
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # return f"{base}_{timestamp}{ext}"
    
    return filepath

@app.route('/upload', methods=['POST'])
def upload_file():
    """Endpoint to handle file uploads"""
    # Check if the post request has the file part
    if 'file' not in request.files:
        logger.warning("No file part in request")
        return jsonify({
            'success': False,
            'error': 'No file part in request'
        }), 400
    
    file = request.files['file']
    
    # If user does not select file, browser submits an empty part without filename
    if file.filename == '':
        logger.warning("No file selected")
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    #if file and allowed_file(file.filename):
    if file:
        # Secure the filename
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Get unique filename (or same for overwriting)
        filepath = get_unique_filename(filepath)
        
        try:
            # Save the file
            file.save(filepath)
            
            # Get file info
            file_size = os.path.getsize(filepath)
            logger.info(f"File uploaded: {filename} ({file_size} bytes)")
            
            return jsonify({
                'success': True,
                'message': 'File uploaded successfully',
                'filename': filename,
                'filepath': filepath,
                'size': file_size,
                'timestamp': datetime.now().isoformat()
            }), 200
        
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Error saving file: {str(e)}'
            }), 500
    
    else:
        logger.warning(f"File type not allowed: {file.filename}")
        return jsonify({
            'success': False,
            'error': 'File type not allowed',
            'allowed_extensions': list(ALLOWED_EXTENSIONS)
        }), 400

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'folder_exists': os.path.exists(app.config['UPLOAD_FOLDER']),
        'max_file_size': app.config['MAX_CONTENT_LENGTH']
    }), 200

@app.route('/files', methods=['GET'])
def list_files():
    """List all uploaded files"""
    try:
        files = []
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    files.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files),
            'upload_folder': app.config['UPLOAD_FOLDER']
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error listing files: {str(e)}'
        }), 500

@app.route('/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a specific file"""
    try:
        # Secure the filename
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        # Delete the file
        os.remove(filepath)
        logger.info(f"File deleted: {safe_filename}")
        
        return jsonify({
            'success': True,
            'message': 'File deleted successfully',
            'filename': safe_filename
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error deleting file: {str(e)}'
        }), 500

@app.route('/cleanup', methods=['DELETE'])
def cleanup_files():
    """Delete all uploaded files"""
    try:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            return jsonify({
                'success': False,
                'error': 'Upload folder does not exist'
            }), 404
        
        files_deleted = 0
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
                files_deleted += 1
        
        logger.info(f"Cleaned up {files_deleted} files")
        
        return jsonify({
            'success': True,
            'message': f'Deleted {files_deleted} files',
            'files_deleted': files_deleted
        }), 200
    
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error during cleanup: {str(e)}'
        }), 500

@app.route('/')
def index():
    """Root endpoint with API information"""
    return jsonify({
        'service': 'File Upload Server',
        'version': '1.0.0',
        'endpoints': {
            'upload': {'method': 'POST', 'path': '/upload', 'description': 'Upload a file'},
            'list_files': {'method': 'GET', 'path': '/files', 'description': 'List all uploaded files'},
            'delete_file': {'method': 'DELETE', 'path': '/files/<filename>', 'description': 'Delete a specific file'},
            'cleanup': {'method': 'DELETE', 'path': '/cleanup', 'description': 'Delete all uploaded files'},
            'health': {'method': 'GET', 'path': '/health', 'description': 'Health check'}
        },
        'config': {
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'max_file_size': f"{app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.1f} MB"
        }
    }), 200

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({
        'success': False,
        'error': f'File too large. Maximum size is {MAX_CONTENT_LENGTH / (1024*1024):.1f} MB'
    }), 413

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(e)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    # Create uploads directory if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Print startup information
    print("=" * 60)
    print("File Upload Server")
    print("=" * 60)
    print(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"Max file size: {MAX_CONTENT_LENGTH / (1024*1024):.1f} MB")
    print(f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    print("=" * 60)
    print("Available endpoints:")
    print("  POST   /upload     - Upload a file")
    print("  GET    /files      - List all uploaded files")
    print("  DELETE /files/<name> - Delete a specific file")
    print("  DELETE /cleanup    - Delete all uploaded files")
    print("  GET    /health     - Health check")
    print("  GET    /           - API information")
    print("=" * 60)
    print(f"Server starting on http://localhost:8888")
    print("=" * 60)
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=8888,
        debug=False,
        threaded=True
    )