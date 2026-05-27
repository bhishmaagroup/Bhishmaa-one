from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.blueprints.notifications import notifications_bp
from app.models.notifications import Notification
from app.blueprints.notifications.services import mark_notification_as_read, mark_all_read_for_user

@notifications_bp.route('/')
@login_required
def list_notifications():
    """
    Renders user notification inbox list.
    """
    # Fetch all read/unread notifications for current user/broadcast
    notifications = Notification.query.filter(
        Notification.organization_id == current_user.organization_id,
        Notification.is_deleted == False,
        or_(Notification.user_id == current_user.id, Notification.user_id == None)
    ).order_by(Notification.is_read.asc(), Notification.created_at.desc()).all()
    
    return render_template(
        'notifications/notifications_list.html',
        notifications=notifications
    )

@notifications_bp.route('/read/<notif_id>')
@login_required
def read_notification_route(notif_id):
    """
    Marks a notification as read and redirects to its target destination path.
    """
    notif = mark_notification_as_read(notif_id, current_user.organization_id)
    
    if notif and notif.link:
        return redirect(notif.link)
    
    return redirect(url_for('dashboard.index'))

@notifications_bp.route('/clear-all', methods=['POST'])
@login_required
def clear_all_notifications_route():
    """
    Marks all user notifications as read.
    """
    count = mark_all_read_for_user(current_user.organization_id, current_user.id)
    flash(f"Cleared {count} unread notifications.", "success")
    return redirect(url_for('notifications.list_notifications'))
