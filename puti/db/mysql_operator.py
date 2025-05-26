"""
数据库操作工具，基于MysqlConfig配置，封装常用操作
"""
import pymysql
from puti.conf.mysql_conf import MysqlConfig


class MysqlOperator:
    def __init__(self):
        self.config = MysqlConfig()
        self.conn = None
        self.cursor = None

    def connect(self):
        if self.conn is None:
            self.conn = pymysql.connect(
                host=self.config.HOSTNAME,
                port=self.config.PORT,
                user=self.config.USERNAME,
                password=self.config.PASSWORD,
                database=self.config.DB_NAME,
                charset='utf8mb4'
            )
            self.cursor = self.conn.cursor()

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, sql, params=None):
        self.connect()
        self.cursor.execute(sql, params or ())
        self.conn.commit()
        return self.cursor

    def fetchone(self, sql, params=None):
        self.connect()
        self.cursor.execute(sql, params or ())
        return self.cursor.fetchone()

    def fetchall(self, sql, params=None):
        self.connect()
        self.cursor.execute(sql, params or ())
        return self.cursor.fetchall()

    def insert(self, sql, params=None):
        self.connect()
        self.cursor.execute(sql, params or ())
        self.conn.commit()
        return self.cursor.lastrowid

    def update(self, sql, params=None):
        self.connect()
        self.cursor.execute(sql, params or ())
        self.conn.commit()
        return self.cursor.rowcount

    def delete(self, sql, params=None):
        self.connect()
        self.cursor.execute(sql, params or ())
        self.conn.commit()
        return self.cursor.rowcount

    def begin(self):
        self.connect()
        self.conn.begin()

    def commit(self):
        if self.conn:
            self.conn.commit()

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
