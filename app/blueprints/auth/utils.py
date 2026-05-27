import jwt
import datetime
from flask import current_app

def parse_device_type(user_agent_string):
    """
    Parses a User-Agent string to approximate device type.
    """
    if not user_agent_string:
        return 'Unknown'
        
    ua = user_agent_string.lower()
    if 'ipad' in ua or 'android' in ua and 'mobile' not in ua:
        return 'Tablet'
    elif 'mobile' in ua or 'iphone' in ua or 'ipod' in ua:
        return 'Mobile'
    else:
        return 'Desktop'

def generate_jwt_token(payload_data, expiry_minutes=60):
    """
    Generates a secure JWT token signed with application key.
    """
    try:
        payload = payload_data.copy()
        payload['exp'] = datetime.datetime.utcnow() + datetime.timedelta(minutes=expiry_minutes)
        payload['iat'] = datetime.datetime.utcnow()
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    except Exception:
        return None

def verify_jwt_token(token):
    """
    Verifies and decodes a JWT token.
    """
    try:
        return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
