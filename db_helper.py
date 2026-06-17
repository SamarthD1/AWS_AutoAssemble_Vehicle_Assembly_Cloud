import mysql.connector
from mysql.connector import pooling
from config import Config
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize connection pool
try:
    db_config = {
        "host": Config.DB_HOST,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "database": Config.DB_NAME,
        "port": Config.DB_PORT
    }
    
    # Create a connection pool with size 5
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="auto_assemble_pool",
        pool_size=5,
        pool_reset_session=True,
        **db_config
    )
    logger.info("Database connection pool established successfully.")
except mysql.connector.Error as err:
    logger.error(f"Failed to create connection pool: {err}")
    connection_pool = None

def get_connection():
    """Gets a connection from the connection pool."""
    if not connection_pool:
        raise ConnectionError("Database connection pool is not initialized.")
    try:
        return connection_pool.get_connection()
    except mysql.connector.Error as err:
        logger.error(f"Failed to get connection from pool: {err}")
        raise

def execute_query(query, params=None):
    """
    Executes a SELECT query and returns the results as a list of dictionaries.
    Guards against SQL injection by using parameterized inputs.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        # Using dictionary=True returns rows as dicts: {'col_name': value}
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        result = cursor.fetchall()
        return result
    except mysql.connector.Error as err:
        logger.error(f"Error executing query: {query}. Error: {err}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def execute_update(query, params=None, return_lastrowid=False):
    """
    Executes an INSERT, UPDATE, or DELETE query.
    Returns the number of affected rows, or the last inserted ID.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        if return_lastrowid:
            return cursor.lastrowid
        return cursor.rowcount
    except mysql.connector.Error as err:
        logger.error(f"Error executing update: {query}. Error: {err}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def log_activity(user_id, action, details=None):
    """
    Utility function to log user activity into the database.
    """
    query = """
        INSERT INTO activity_logs (user_id, action, details)
        VALUES (%s, %s, %s)
    """
    try:
        execute_update(query, (user_id, action, details))
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
