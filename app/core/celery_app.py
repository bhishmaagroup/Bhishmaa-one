from celery import Celery

# Create the global Celery instance
celery = Celery('bhishmaa_one')

def init_celery(app):
    """
    Initializes Celery instance with configuration from Flask config.
    Wraps task execution within the Flask application context.
    """
    celery.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        task_ignore_result=True,
        timezone='Asia/Kolkata'
    )
    
    # Auto-enable eager execution for testing or offline environment fallback
    if app.config.get('TESTING') or not app.config.get('CELERY_BROKER_URL') or app.config.get('CELERY_BROKER_URL') == 'offline':
        celery.conf.update(
            task_always_eager=True,
            task_eager_propagates=True
        )
        
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
                
    celery.Task = ContextTask
    return celery
