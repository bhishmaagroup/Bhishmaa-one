import os
from dotenv import load_dotenv

# Load env values
load_dotenv()

from app.core import create_app, db

# Factory invocation
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    with app.app_context():
        # Auto-create tables for SQLite / development postgres setups
        db.create_all()
        
        # Seed default roles and permissions
        from app.blueprints.roles.services import seed_roles_and_permissions
        seed_roles_and_permissions()
        
    print(f"Bhishmaa One running in {config_name} mode on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000)
