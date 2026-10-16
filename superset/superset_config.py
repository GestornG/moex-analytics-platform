import os

from sqlalchemy.engine import URL


SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

SQLALCHEMY_DATABASE_URI = URL.create(
    drivername="postgresql+psycopg2",
    username="superset_meta",
    password=os.environ["SUPERSET_META_PASSWORD"],
    host="moex-postgres",
    port=5432,
    database="superset_metadata",
).render_as_string(hide_password=False)
