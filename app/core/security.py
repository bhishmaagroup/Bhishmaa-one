"""
Security utilities for Bhishmaa One ERP.

Provides:
- Secure password handling
- File upload validation
- CSRF protection helpers
- Session security
"""

import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash


class SecurityConfig:
    """Security configuration constants."""
    
    # File upload settings
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'csv', 'xlsx', 'xls'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
    UPLOAD_FOLDER = 'uploads'
    
    # Password settings
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_SPECIAL_CHARS = True
    REQUIRE_NUMBERS = True
    REQUIRE_UPPERCASE = True


def check_file_signature(file_stream, ext):
    """
    Validates file integrity using magic number signature matching.
    Supports png, jpg, jpeg, gif, pdf, xls, xlsx, csv.
    """
    header = file_stream.read(8)
    file_stream.seek(0)
    
    ext = ext.lower()
    if ext in ['jpg', 'jpeg']:
        return header.startswith(b'\xff\xd8\xff')
    elif ext == 'png':
        return header.startswith(b'\x89PNG\r\n\x1a\n')
    elif ext == 'gif':
        return header.startswith(b'GIF87a') or header.startswith(b'GIF89a')
    elif ext == 'pdf':
        return header.startswith(b'%PDF')
    elif ext == 'xlsx':
        return header.startswith(b'PK\x03\x04')
    elif ext == 'xls':
        return header.startswith(b'\xd0\xcf\x11\xe0')
    elif ext == 'csv':
        try:
            sample = file_stream.read(1024)
            file_stream.seek(0)
            if b'\x00' in sample:
                return False
            sample.decode('utf-8')
            return True
        except Exception:
            return False
    return True


def validate_file_upload(file, allowed_extensions=None, max_size=None):
    """
    Validate uploaded file safety.
    
    Args:
        file: Flask FileStorage object
        allowed_extensions: Set of allowed file extensions (defaults to ALLOWED_EXTENSIONS)
        max_size: Max file size in bytes (defaults to MAX_FILE_SIZE)
        
    Returns:
        Tuple (is_valid, error_message)
    """
    if allowed_extensions is None:
        allowed_extensions = SecurityConfig.ALLOWED_EXTENSIONS
    
    if max_size is None:
        max_size = SecurityConfig.MAX_FILE_SIZE
    
    if not file or file.filename == '':
        return False, 'No file selected'
        
    # Check for path traversal attempts
    if '..' in file.filename or '/' in file.filename or '\\' in file.filename:
        return False, 'Malicious path sequence detected in filename'
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > max_size:
        return False, f'File size exceeds maximum of {max_size / (1024*1024):.1f}MB'
    
    # Check file extension
    filename = secure_filename(file.filename)
    if '.' not in filename:
        return False, 'File must have an extension'
    
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        return False, f'File type .{ext} not allowed'
        
    # Check signature
    if not check_file_signature(file, ext):
        return False, f'File content signature mismatch for type .{ext}'
    
    return True, None


def validate_password(password):
    """
    Validate password strength.
    
    Args:
        password: Password string to validate
        
    Returns:
        Tuple (is_valid, error_message)
    """
    if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
        return False, f'Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters'
    
    if SecurityConfig.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, 'Password must contain at least one uppercase letter'
    
    if SecurityConfig.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
        return False, 'Password must contain at least one number'
    
    if SecurityConfig.REQUIRE_SPECIAL_CHARS:
        special_chars = set('!@#$%^&*()_+-=[]{}|;:,.<>?')
        if not any(c in special_chars for c in password):
            return False, 'Password must contain at least one special character'
    
    return True, None


def hash_password(password):
    """
    Hash password using werkzeug.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)


def verify_password(password, password_hash):
    """
    Verify password against hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Previously hashed password
        
    Returns:
        Boolean indicating if password matches
    """
    return check_password_hash(password_hash, password)


def generate_secure_filename(original_filename, max_length=255):
    """
    Generate secure filename.
    
    Args:
        original_filename: Original filename from upload
        max_length: Maximum filename length
        
    Returns:
        Safe filename string
    """
    filename = secure_filename(original_filename)
    
    # Truncate if too long (keep extension)
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1)
        max_name_length = max_length - len(ext) - 1
        filename = name[:max_name_length] + '.' + ext
    
    return filename
