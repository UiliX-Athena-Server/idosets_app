workers = 3
bind = "0.0.0.0:5000"
wsgi_app = "app:create_app()"


def on_starting(server):
    """
    Pre-runner: runs once in the gunicorn master before any worker starts.

    Building the app here runs the database preparation (migrating and
    removing an old database, or creating a new one) a single time, with no
    worker boot timeout to worry about. The workers then find it done.
    """
    from app import create_app

    create_app()
    server.log.info("Database ready.")
