"""
@Author: obstacles
@Time:  2025-06-25 15:00
@Description: MySQL database operator
"""
import pymysql
import threading
from puti.conf.mysql_conf import MysqlConfig
from puti.logs import logger_factory

lgr = logger_factory.db


class MysqlOperator:
    _connections = threading.local()

    def __init__(self):
        self.config = MysqlConfig()
        if not all([self.config.HOSTNAME, self.config.USERNAME, self.config.PASSWORD, self.config.DB_NAME, self.config.PORT]):
            raise ValueError("MySQL connection details are not fully configured.")

    def connect(self):
        """Establishes a new MySQL connection if one doesn't exist for the current thread."""
        if not hasattr(self._connections, 'conn') or self._connections.conn is None:
            try:
                self._connections.conn = pymysql.connect(
                    host=self.config.HOSTNAME,
                    user=self.config.USERNAME,
                    password=self.config.PASSWORD,
                    database=self.config.DB_NAME,
                    port=self.config.PORT,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
            except pymysql.MySQLError as e:
                lgr.error(f"Error connecting to MySQL database: {e}")
                raise
        return self._connections.conn

    def close(self):
        """Closes the MySQL connection for the current thread."""
        if hasattr(self._connections, 'conn') and self._connections.conn is not None:
            self._connections.conn.close()
            self._connections.conn = None

    def execute(self, sql, params=None):
        """Executes a given SQL query."""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
            conn.commit()
            return cursor
        except pymysql.MySQLError as e:
            lgr.error(f"Error executing query: {sql} with params: {params}. Error: {e}")
            conn.rollback()
            raise

    def fetchone(self, sql, params=None):
        """Fetches a single result from a query."""
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()

    def fetchall(self, sql, params=None):
        """Fetches all results from a query."""
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
