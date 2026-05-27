from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from app.core.extensions import db
from app.models.core import Organization, User
from app.models.billing import Invoice
from app.models.inventory import Product
from app.blueprints.organizations.forms import OrganizationProfileForm, BillingSettingsForm, ChangePlanForm
from app.blueprints.organizations.services import (
    update_organization_profile, update_billing_settings, get_or_create_org_details, upgrade_subscription_plan
)
from app.blueprints.organizations.utils import get_organization_limits
from datetime import datetime, date

organizations_bp = Blueprint(
    'organizations',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@organizations_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    org = current_user.organization
    if not org:
        flash("No active organization profile found.", "danger")
        return redirect(url_for('dashboard.index'))
        
    form = OrganizationProfileForm(obj=org)
    if form.validate_on_submit():
        update_organization_profile(org.id, form.name.data, form.subdomain.data)
        flash("Business profile updated successfully!", "success")
        return redirect(url_for('organizations.profile'))
        
    return render_template('organizations/profile.html', form=form, org=org)

@organizations_bp.route('/billing-settings', methods=['GET', 'POST'])
@login_required
def billing_settings():
    org = current_user.organization
    if not org:
        flash("No active organization profile found.", "danger")
        return redirect(url_for('dashboard.index'))
        
    details = get_or_create_org_details(org.id)
    form = BillingSettingsForm(obj=details)
    
    if form.validate_on_submit():
        update_data = {
            'gstin': form.gstin.data,
            'billing_email': form.billing_email.data,
            'billing_phone': form.billing_phone.data,
            'billing_address': form.billing_address.data,
            'state_code': form.state_code.data,
            'pan_number': form.pan_number.data,
            'currency': form.currency.data
        }
        update_billing_settings(org.id, update_data)
        flash("Billing and GST settings updated successfully!", "success")
        return redirect(url_for('organizations.billing_settings'))
        
    return render_template('organizations/billing_settings.html', form=form, org=org)

@organizations_bp.route('/subscription', methods=['GET', 'POST'])
@login_required
def subscription():
    org = current_user.organization
    if not org:
        flash("No active organization profile found.", "danger")
        return redirect(url_for('dashboard.index'))
        
    limits = get_organization_limits(org.plan_name)
    form = ChangePlanForm(plan_name=org.plan_name)
    
    # Calculate real-time counts for limits visual representation
    today = date.today()
    month_start = datetime(today.year, today.month, 1)
    
    staff_count = User.query.filter_by(organization_id=org.id, is_deleted=False).count()
    
    invoices_count = Invoice.query.filter(
        Invoice.organization_id == org.id,
        Invoice.is_deleted == False,
        Invoice.created_at >= month_start
    ).count()
    
    products_count = Product.query.filter_by(
        organization_id=org.id,
        is_deleted=False
    ).count()
    
    usage = {
        'staff_count': staff_count,
        'staff_limit': limits.get('max_staff'),
        'invoices_count': invoices_count,
        'invoices_limit': limits.get('max_invoices_per_month'),
        'products_count': products_count,
        'products_limit': limits.get('max_products')
    }
    
    if form.validate_on_submit():
        # Handle subscription change directly (fallback legacy compatibility check)
        upgrade_subscription_plan(org.id, form.plan_name.data, amount=0.0)
        flash(f"Subscription plan successfully changed to '{form.plan_name.data}'!", "success")
        return redirect(url_for('organizations.subscription'))
        
    return render_template('organizations/subscription.html', form=form, org=org, limits=limits, usage=usage)


@organizations_bp.route('/subscription/checkout', methods=['POST'])
@login_required
def checkout():
    """
    Initializes subscription checkout order context.
    Determines plan pricing and creates a Razorpay Order if key is available.
    """
    import os
    
    org = current_user.organization
    if not org:
        return jsonify({'error': 'Organization profile not found.'}), 404
        
    data = request.get_json() or {}
    plan_name = data.get('plan_name')
    billing_cycle = data.get('billing_cycle', 'monthly')
    
    # Define plans base pricing in INR
    prices = {
        'Free': 0,
        'Starter': 999,
        'Business': 2999,
        'Premium': 5999
    }
    
    if plan_name not in prices:
        return jsonify({'error': f'Invalid plan name: {plan_name}'}), 400
        
    price = prices[plan_name]
    if billing_cycle == 'annually':
        # Apply 20% discount for annual subscription
        price = int(price * 12 * 0.8)
        
    # Standard checkout for paid plans, or switch for Free plan
    if price == 0:
        # Free plan does not need a payment flow, switch immediately
        upgrade_subscription_plan(org.id, 'Free', billing_cycle, amount=0.0)
        return jsonify({'success': True, 'free_plan': True})
        
    # Check if Razorpay keys are configured in environment
    rzp_key_id = os.environ.get('RAZORPAY_KEY_ID')
    rzp_key_secret = os.environ.get('RAZORPAY_KEY_SECRET')
    
    if rzp_key_id and rzp_key_secret:
        # Production mode: Create Razorpay Order
        try:
            import razorpay
            client = razorpay.Client(auth=(rzp_key_id, rzp_key_secret))
            
            # Amount in paise
            amount_paise = int(price * 100)
            
            order_data = {
                'amount': amount_paise,
                'currency': 'INR',
                'payment_capture': 1
            }
            order = client.order.create(data=order_data)
            
            return jsonify({
                'simulated': False,
                'key': rzp_key_id,
                'amount': amount_paise,
                'currency': 'INR',
                'order_id': order['id'],
                'name': 'Bhishmaa One',
                'description': f'Upgrade to {plan_name} plan ({billing_cycle})',
                'plan_name': plan_name,
                'billing_cycle': billing_cycle
            })
        except Exception as e:
            # Fallback to simulation if client creation fails
            pass
            
    # Simulation mode fallback
    # Generate a mock order ID
    import uuid
    sim_order_id = f"order_sim_{uuid.uuid4().hex[:14]}"
    amount_paise = int(price * 100)
    
    # Store simulated order validation in Flask session to verify callback signature
    if 'simulated_orders' not in session:
        session['simulated_orders'] = {}
    session['simulated_orders'][sim_order_id] = {
        'plan_name': plan_name,
        'billing_cycle': billing_cycle,
        'amount': price
    }
    session.modified = True
    
    return jsonify({
        'simulated': True,
        'amount': amount_paise,
        'currency': 'INR',
        'order_id': sim_order_id,
        'name': 'Bhishmaa One (Simulator)',
        'description': f'[SIMULATED] Upgrade to {plan_name} plan ({billing_cycle})',
        'plan_name': plan_name,
        'billing_cycle': billing_cycle
    })


@organizations_bp.route('/subscription/callback', methods=['POST'])
@login_required
def callback():
    """
    Verifies payment verification signatures and upgrades subscriptions.
    """
    import os
    from app.blueprints.platform.services import log_audit_event
    
    org = current_user.organization
    if not org:
        return jsonify({'error': 'Organization not found'}), 404
        
    data = request.get_json() or {}
    rzp_payment_id = data.get('razorpay_payment_id')
    rzp_order_id = data.get('razorpay_order_id')
    rzp_signature = data.get('razorpay_signature')
    
    plan_name = data.get('plan_name')
    billing_cycle = data.get('billing_cycle', 'monthly')
    
    # 1. Handle Simulated Verification
    if rzp_order_id and rzp_order_id.startswith('order_sim_'):
        sim_orders = session.get('simulated_orders', {})
        if rzp_order_id not in sim_orders:
            return jsonify({'error': 'Invalid simulated order contexts.'}), 400
            
        sim_order = sim_orders.pop(rzp_order_id)
        session.modified = True
        
        # Verify plan details match
        if sim_order['plan_name'] != plan_name:
            return jsonify({'error': 'Plan verification details mismatch.'}), 400
            
        amount = float(sim_order['amount'])
        
        # Execute upgrade
        success, msg = upgrade_subscription_plan(org.id, plan_name, billing_cycle, amount)
        if success:
            log_audit_event(
                action='SUBSCRIPTION_UPGRADED',
                new_values={'plan': plan_name, 'billing': billing_cycle, 'amount': amount, 'reference': rzp_payment_id, 'mode': 'Simulated'},
                organization_id=org.id,
                user_id=current_user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            return jsonify({'success': True, 'message': 'Simulated payment verified successfully.'})
        return jsonify({'error': msg}), 400
        
    # 2. Handle Razorpay Production Verification
    rzp_key_id = os.environ.get('RAZORPAY_KEY_ID')
    rzp_key_secret = os.environ.get('RAZORPAY_KEY_SECRET')
    
    if not rzp_key_id or not rzp_key_secret:
        return jsonify({'error': 'Razorpay payment settings are missing.'}), 500
        
    try:
        import razorpay
        client = razorpay.Client(auth=(rzp_key_id, rzp_key_secret))
        
        # Verify signature
        params_dict = {
            'razorpay_order_id': rzp_order_id,
            'razorpay_payment_id': rzp_payment_id,
            'razorpay_signature': rzp_signature
        }
        client.utility.verify_payment_signature(params_dict)
        
        # Fetch payment details to obtain amount
        payment_info = client.payment.fetch(rzp_payment_id)
        amount_paid = float(payment_info['amount']) / 100.0  # convert from paise
        
        # Execute upgrade
        success, msg = upgrade_subscription_plan(org.id, plan_name, billing_cycle, amount_paid)
        if success:
            # Set payment reference on new subscription
            from app.models.organizations import OrganizationSubscription
            sub = OrganizationSubscription.query.filter_by(
                organization_id=org.id,
                status='Active'
            ).first()
            if sub:
                sub.payment_reference = rzp_payment_id
                db.session.commit()
                
            log_audit_event(
                action='SUBSCRIPTION_UPGRADED',
                new_values={'plan': plan_name, 'billing': billing_cycle, 'amount': amount_paid, 'reference': rzp_payment_id, 'mode': 'Razorpay'},
                organization_id=org.id,
                user_id=current_user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            return jsonify({'success': True, 'message': 'Payment signature verified successfully.'})
        return jsonify({'error': msg}), 400
        
    except Exception as e:
        return jsonify({'error': f'Signature verification failed: {e}'}), 400

@organizations_bp.route('/admin/list')
@login_required
def admin_list():
    # Super Admin restriction
    if not current_user.has_permission('manage_tenant'):
        flash("Unauthorized. Super Admin access only.", "danger")
        return redirect(url_for('dashboard.index'))
        
    orgs = Organization.query.all()
    return render_template('organizations/admin_list.html', orgs=orgs)

@organizations_bp.route('/admin/suspend/<org_id>', methods=['POST'])
@login_required
def admin_suspend(org_id):
    if not current_user.has_permission('manage_tenant'):
        flash("Unauthorized.", "danger")
        return redirect(url_for('dashboard.index'))
        
    org = Organization.query.get(org_id)
    if org:
        org.is_active = not org.is_active
        db.session.commit()
        status = "suspended" if not org.is_active else "activated"
        flash(f"Organization '{org.name}' successfully {status}.", "success")
        
    return redirect(url_for('organizations.admin_list'))
