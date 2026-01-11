from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
import logging
from datetime import datetime
from typing import Optional, Tuple

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

def _realpath(path: str) -> str:
    return os.path.realpath(path)

def resolve_path_under_upload(rel_path: str) -> Tuple[str, str]:
    """
    Resolve a user-provided relative path safely under UPLOAD_FOLDER.
    Returns: (absolute_path, normalized_relative_path)
    """
    if rel_path is None:
        raise ValueError("path is required")

    # Treat both / and \ as separators, forbid absolute paths / traversal.
    rel = str(rel_path).replace('\\', '/').lstrip('/')
    norm = os.path.normpath(rel)

    if norm in ("", ".") or norm.startswith("..") or os.path.isabs(norm):
        raise ValueError("invalid relative path")

    base = _realpath(app.config['UPLOAD_FOLDER'])
    full = _realpath(os.path.join(base, norm))

    # Ensure 'full' stays within 'base'
    if full != base and not full.startswith(base + os.sep):
        raise ValueError("path escapes upload folder")

    return full, norm.replace('\\', '/')

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
        # Optional: allow uploading into a subdirectory with a relative path.
        # This is used for directory sync; file uploads without this keep the old behavior.
        relative_path = request.form.get('relative_path')

        if relative_path:
            try:
                filepath, normalized_rel = resolve_path_under_upload(relative_path)
                filename = os.path.basename(normalized_rel)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
            except Exception as e:
                logger.warning(f"Invalid relative_path='{relative_path}': {str(e)}")
                return jsonify({
                    'success': False,
                    'error': f'Invalid relative_path: {str(e)}'
                }), 400
        else:
            # Secure the filename (legacy behavior)
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
                'relative_path': relative_path,
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

@app.route('/dir_files', methods=['GET'])
def list_directory_files():
    """
    List all files (recursively) under a directory within the upload folder.
    Query params:
      - dir: relative directory under UPLOAD_FOLDER (e.g. "Photos/2025"). If omitted, uses upload root.
    Response file paths are relative to the requested directory root.
    """
    try:
        rel_dir = request.args.get('dir', '').strip()
        if rel_dir in ('', '.'):
            base_dir = _realpath(app.config['UPLOAD_FOLDER'])
            dir_norm = ''
        else:
            base_dir, dir_norm = resolve_path_under_upload(rel_dir)

        if not os.path.exists(base_dir):
            return jsonify({
                'success': True,
                'dir': dir_norm,
                'files': [],
                'count': 0
            }), 200

        if not os.path.isdir(base_dir):
            return jsonify({
                'success': False,
                'error': 'dir is not a directory',
                'dir': dir_norm
            }), 400

        files = []
        for root_dir, _, filenames in os.walk(base_dir):
            for name in filenames:
                full_path = os.path.join(root_dir, name)
                if not os.path.isfile(full_path):
                    continue
                stat = os.stat(full_path)
                rel_path = os.path.relpath(full_path, base_dir).replace('\\', '/')
                files.append({
                    'path': rel_path,
                    'size': stat.st_size
                })

        return jsonify({
            'success': True,
            'dir': dir_norm,
            'files': files,
            'count': len(files)
        }), 200

    except Exception as e:
        logger.error(f"Error listing directory files: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error listing directory files: {str(e)}'
        }), 500

@app.route('/file', methods=['DELETE'])
def delete_file_by_path():
    """
    Delete a file by relative path under the upload folder.
    Query params:
      - path: relative path to the file (e.g. "Photos/2025/img001.jpg")
    """
    try:
        rel_path = request.args.get('path')
        if not rel_path:
            return jsonify({
                'success': False,
                'error': 'path is required'
            }), 400

        filepath, norm = resolve_path_under_upload(rel_path)

        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'File not found',
                'path': norm
            }), 404

        if not os.path.isfile(filepath):
            return jsonify({
                'success': False,
                'error': 'Path is not a file',
                'path': norm
            }), 400

        os.remove(filepath)
        logger.info(f"File deleted by path: {norm}")

        return jsonify({
            'success': True,
            'message': 'File deleted successfully',
            'path': norm
        }), 200

    except Exception as e:
        logger.error(f"Error deleting file by path: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error deleting file by path: {str(e)}'
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
            'list_directory_files': {'method': 'GET', 'path': '/dir_files?dir=<relative_dir>', 'description': 'List files+sizes under a directory (recursive)'},
            'delete_file_by_path': {'method': 'DELETE', 'path': '/file?path=<relative_path>', 'description': 'Delete a file by relative path'},
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
    print("  GET    /dir_files?dir=<relative_dir> - List files under a directory")
    print("  DELETE /file?path=<relative_path> - Delete a file by relative path")
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