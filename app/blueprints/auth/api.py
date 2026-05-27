from flask import request, jsonify
from app.blueprints.auth.routes import auth_bp
from app.models.core import User
from app.blueprints.auth.services import log_login_attempt, generate_otp, verify_otp
from app.blueprints.auth.utils import generate_jwt_token

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """
    REST API Endpoint to authenticate users and issue secure JWT tokens.
    """
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username and password are required.'}), 400
        
    user = User.query.filter_by(username=username).first()
    ip_addr = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    
    if user and user.check_password(password) and user.is_active:
        log_login_attempt(user.id, ip_addr, ua, 'Success')
        
        # Issue JWT
        token = generate_jwt_token({
            'sub': user.id,
            'org': user.organization_id,
            'username': user.username
        })
        return jsonify({
            'token': token,
            'user': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        }), 200
        
    if user:
        log_login_attempt(user.id, ip_addr, ua, 'Failed')
        
    return jsonify({'message': 'Invalid credentials.'}), 401

@auth_bp.route('/api/otp/request', methods=['POST'])
def api_otp_request():
    """
    Requests a numeric verification OTP.
    """
    data = request.get_json() or {}
    email = data.get('email')
    purpose = data.get('purpose', 'login')
    
    if not email:
        return jsonify({'message': 'Email address is required.'}), 400
        
    generate_otp(email, purpose)
    return jsonify({'message': 'Verification code sent successfully.'}), 200

@auth_bp.route('/api/otp/verify', methods=['POST'])
def api_otp_verify():
    """
    Verifies OTP and issues a JWT token.
    """
    data = request.get_json() or {}
    email = data.get('email')
    otp_code = data.get('otp_code')
    purpose = data.get('purpose', 'login')
    
    if not email or not otp_code:
        return jsonify({'message': 'Email and OTP code are required.'}), 400
        
    valid, message = verify_otp(email, otp_code, purpose)
    if not valid:
        return jsonify({'message': message}), 400
        
    # Resolve user and issue token
    user = User.query.filter_by(email=email.lower()).first()
    if not user:
        return jsonify({'message': 'OTP verified successfully, but no user profile is linked.'}), 200
        
    token = generate_jwt_token({
        'sub': user.id,
        'org': user.organization_id,
        'username': user.username
    })
    return jsonify({
        'token': token,
        'message': 'OTP verification completed successfully.'
    }), 200
stream = True
