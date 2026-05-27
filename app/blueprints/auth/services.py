import secrets
import random
import datetime
from flask import current_app
from flask_mail import Message
from werkzeug.security import generate_password_hash
from app.core.extensions import db, mail
from app.models.core import User, Organization
from app.models.auth import LoginHistory, UserSession, OTPVerification
from app.blueprints.auth.utils import parse_device_type, generate_jwt_token, verify_jwt_token
from app.blueprints.auth.constants import OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS, SESSION_EXPIRY_DAYS, PURPOSE_PASSWORD_RESET

def log_login_attempt(user_id, ip_address, user_agent, status='Success'):
    """
    Logs login attempt into the database with device detection.
    """
    device_type = parse_device_type(user_agent)
    history = LoginHistory(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent[:255],
        status=status,
        device_type=device_type
    )
    db.session.add(history)
    db.session.commit()
    return history

def create_user_session(user_id, ip_address, user_agent):
    """
    Creates an active user session in the database.
    """
    session_token = secrets.token_hex(32)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=SESSION_EXPIRY_DAYS)
    
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        ip_address=ip_address,
        user_agent=user_agent[:255],
        expires_at=expires_at
    )
    db.session.add(session)
    db.session.commit()
    return session_token

def invalidate_user_session(session_token):
    """
    Invalidates a user session token.
    """
    session = UserSession.query.filter_by(session_token=session_token).first()
    if session:
        session.is_active = False
        db.session.commit()
        return True
    return False

def generate_otp(email, purpose):
    """
    Generates a 6-digit numeric OTP and stores its hash in database.
    """
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    # Hash OTP code
    otp_hash = generate_password_hash(otp_code)
    
    verification = OTPVerification(
        email=email.lower(),
        otp_code_hash=otp_hash,
        purpose=purpose,
        expires_at=expires_at
    )
    db.session.add(verification)
    db.session.commit()
    
    # In a real SaaS, we would send this via SMS / WhatsApp / Email.
    # We will log it here so it can be verified easily in development console.
    print(f"\n[OTP DISPATCH] Send to: {email} | Code: {otp_code} | Purpose: {purpose}\n")
    return otp_code

def verify_otp(email, otp_code, purpose):
    """
    Verifies OTP code and checks attempts and expiry.
    """
    verification = OTPVerification.query.filter_by(
        email=email.lower(),
        purpose=purpose,
        is_used=False
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if not verification:
        return False, "No active OTP request found."
        
    if verification.is_expired():
        return False, "OTP has expired. Please request a new one."
        
    verification.attempts += 1
    if verification.attempts > OTP_MAX_ATTEMPTS:
        verification.is_used = True
        db.session.commit()
        return False, "Too many failed attempts. Request a new OTP."
        
    if verification.otp_code_hash and verification.otp_code_hash.startswith('pbkdf2:sha256'):
        # For compatibility with legacy hash configurations in werkzeug
        from werkzeug.security import check_password_hash
        valid = check_password_hash(verification.otp_code_hash, otp_code)
    else:
        from werkzeug.security import check_password_hash
        valid = check_password_hash(verification.otp_code_hash, otp_code)
        
    if not valid:
        db.session.commit()
        return False, f"Invalid OTP code. Attempts remaining: {OTP_MAX_ATTEMPTS - verification.attempts}"
        
    # Mark as successfully verified
    verification.is_used = True
    db.session.commit()
    return True, "OTP verified successfully."

def initiate_password_reset(email):
    """
    Creates a JWT token for password reset and sends reset email.
    """
    user = User.query.filter_by(email=email.lower()).first()
    if not user:
        # Avoid user enumeration attacks: return true even if email not found
        return True
        
    # Build secure token
    token = generate_jwt_token({'sub': user.id, 'purpose': PURPOSE_PASSWORD_RESET}, expiry_minutes=30)
    
    # Try sending mail
    try:
        msg = Message(
            subject="Bhishmaa One - Password Reset Request",
            recipients=[user.email],
            body=f"Hello,\n\nPlease click the following link to reset your password:\n"
                 f"http://127.0.0.1:5000/auth/reset-password?token={token}\n\n"
                 f"If you did not request this, please ignore this email.\n"
        )
        mail.send(msg)
    except Exception as e:
        # Log error in mail delivery, but do not block execution
        print(f"[Mail Error] Failed to send password reset: {e}")
        
    print(f"\n[PASSWORD RESET] Token generated for {email}: {token}\n")
    return True

def complete_password_reset(token, new_password):
    """
    Verifies JWT token and updates user's password.
    """
    data = verify_jwt_token(token)
    if not data or data.get('purpose') != PURPOSE_PASSWORD_RESET:
        return False, "Invalid or expired password reset link."
        
    user_id = data.get('sub')
    user = User.query.get(user_id)
    if not user:
        return False, "User account not found."
        
    user.set_password(new_password)
    db.session.commit()
    return True, "Password reset successfully completed."
