from sqlalchemy import or_
from app.core.extensions import db
from app.models.notifications import Notification

def create_notification(organization_id, title, message, type='System', user_id=None, link=None):
    """
    Saves a system notification / alert log.
    """
    notification = Notification(
        organization_id=organization_id,
        tenant_id=organization_id,
        title=title.strip(),
        message=message.strip(),
        type=type,
        user_id=user_id,
        link=link
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def mark_notification_as_read(notification_id, organization_id):
    """
    Marks a single notification as read.
    """
    notif = Notification.query.filter_by(
        id=notification_id,
        organization_id=organization_id,
        is_deleted=False
    ).first()
    
    if notif:
        notif.is_read = True
        db.session.commit()
        return notif
    return None

def mark_all_read_for_user(organization_id, user_id):
    """
    Marks all unread alerts for a specific staff member (and broadcasts) as read.
    """
    unreads = Notification.query.filter(
        Notification.organization_id == organization_id,
        Notification.is_read == False,
        Notification.is_deleted == False,
        or_(Notification.user_id == user_id, Notification.user_id == None)
    ).all()
    
    for notif in unreads:
        notif.is_read = True
        
    db.session.commit()
    return len(unreads)
