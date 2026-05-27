import os
from flask import Flask
from config import config_by_name
from app.core.extensions import db, migrate, login_manager, mail, csrf, cache
from werkzeug.exceptions import HTTPException, default_exceptions

class PaymentRequired(HTTPException):
    code = 402
    description = 'Payment Required'

default_exceptions[402] = PaymentRequired

def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'development')
        
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    
    # Import database models to register metadata
    from app.models.core import Base, Organization, User, Role, Permission, PlatformUser, Branch
    from app.models.auth import LoginHistory, UserSession, OTPVerification
    from app.models.organizations import OrganizationSubscription, OrganizationDetail
    from app.models.users import UserDetail
    from app.models.billing import Invoice, InvoiceItem, Payment
    from app.models.inventory import Product, Category, Brand, Unit, StockTransaction, BranchStock, StockTransfer, StockTransferItem
    from app.models.crm import Customer, Supplier, CustomerTransaction, SupplierTransaction
    from app.models.hrm import Attendance, SalarySlip
    from app.models.expenses import Expense
    from app.models.notifications import Notification
    from app.models.pos import CashRegisterSession
    from app.models.saas_extensions import FinancialYear, InvoiceSequence, PosTerminal, TaxConfig, Setting, OfflineSyncQueue
    
    # User loader definition
    @login_manager.user_loader
    def load_user(user_id):
        if user_id and user_id.startswith('platform_'):
            real_id = user_id.replace('platform_', '')
            return PlatformUser.query.get(real_id)
        return User.query.get(user_id)
        
    # Register request-level isolation middleware
    from app.middleware.isolation import enforce_tenant_isolation
    app.before_request(enforce_tenant_isolation)
    
    # Inject current_app globally for Jinja2 templates
    @app.context_processor
    def inject_current_app():
        from flask import current_app
        return dict(current_app=current_app)
        
    @app.context_processor
    def inject_notifications():
        from flask_login import current_user
        if current_user.is_authenticated and hasattr(current_user, 'organization_id'):
            from app.models.notifications import Notification
            from sqlalchemy import or_
            unreads = Notification.query.filter(
                Notification.organization_id == current_user.organization_id,
                Notification.is_read == False,
                Notification.is_deleted == False,
                or_(Notification.user_id == current_user.id, Notification.user_id == None)
            ).order_by(Notification.created_at.desc()).limit(5).all()
            
            count = Notification.query.filter(
                Notification.organization_id == current_user.organization_id,
                Notification.is_read == False,
                Notification.is_deleted == False,
                or_(Notification.user_id == current_user.id, Notification.user_id == None)
            ).count()
            
            return dict(unread_notifications=unreads, unread_count=count)
        return dict(unread_notifications=[], unread_count=0)
        
    # Register blueprints (Phase 1)
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.organizations import organizations_bp
    from app.blueprints.users import users_bp
    from app.blueprints.roles import roles_bp
    from app.blueprints.billing import billing_bp
    from app.blueprints.inventory import inventory_bp
    from app.blueprints.crm import crm_bp
    from app.blueprints.hrm import hrm_bp
    from app.blueprints.expenses import expenses_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.pos import pos_bp
    
    from app.blueprints.platform import platform_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(organizations_bp, url_prefix='/organizations')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(roles_bp, url_prefix='/roles')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(crm_bp, url_prefix='/crm')
    app.register_blueprint(hrm_bp, url_prefix='/hrm')
    app.register_blueprint(expenses_bp, url_prefix='/expenses')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(platform_bp, url_prefix='/platform')
    
    @app.errorhandler(402)
    def payment_required(error):
        from flask import render_template
        return render_template('errors/402.html', error=error), 402
        
    return app
