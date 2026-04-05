import azure.functions as func
import psycopg2
import os
import logging
from datetime import datetime

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ── Health check ─────────────────────────────────────────────
@app.route(route="health")
def health(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("Health check called")
    return func.HttpResponse(
        '{"status": "ok", "version": "v1"}',
        mimetype="application/json",
        status_code=200
    )

# ── Create table ─────────────────────────────────────────────
@app.route(route="create-table/{table_name}")
def create_table(req: func.HttpRequest) -> func.HttpResponse:
    table_name = req.route_params.get("table_name")
    logger.info(f"Request to create table: {table_name}")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            sslmode="require"
        )
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Table '{table_name}' created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return func.HttpResponse(
            f'{{"message": "Table {table_name} created successfully", "timestamp": "{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"}}',
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Failed: {str(e)}")
        return func.HttpResponse(
            f'{{"error": "{str(e)}"}}',
            mimetype="application/json",
            status_code=500
        )