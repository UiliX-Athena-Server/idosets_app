FROM idosets_app-base:latest
WORKDIR /main

COPY configs/gunicorn.conf.py gunicorn.conf.py
COPY app app
COPY .env .env

RUN mkdir -p instance

# The database is created, or migrated from the pre-2.0 database.sqlite,
# when gunicorn starts (see on_starting in gunicorn.conf.py).

ENTRYPOINT ["gunicorn", "-c", "gunicorn.conf.py"]
