import datetime
from app.core.extensions import db
from app.models.core import Base, UUIDType

class UserDetail(Base):
    __tablename__ = 'user_details'
    
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(15))
    address = db.Column(db.Text)
    designation = db.Column(db.String(50), default='Staff')
    department = db.Column(db.String(50), default='Operations')
    date_of_joining = db.Column(db.Date, default=datetime.date.today)
    basic_salary = db.Column(db.Numeric(10, 2), default=0.0)

    # Relationships
    user = db.relationship('User', backref=db.backref('detail', uselist=False, lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<UserDetail {self.user_id} - Designation: {self.designation}>"
