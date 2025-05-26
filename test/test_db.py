"""
@Author: obstacle
@Time: 16/01/25 16:26
@Description:  
"""
import datetime

from puti.db import *
from puti.db.model.client.twitter import UserModel, Mentions
from puti.db.model.task.bot_task import BotTask
from puti.db import DBM


def test_db_sqlite():

    pool = SQLiteConnectionPool(str((PuTi.ROOT_DIR.val / 'puti' / 'db' / 'alpha.db')), pool_size=3)
    db_manager = SQLiteManagerWithPool(pool)
    user_handler = SQLiteModelHandlerWithPool(db_manager, UserModel)

    # Create table
    user_handler.create_table()

    # Insert data
    user = UserModel(name="Alice", age=25, email="alice@example.com")
    user_id = user_handler.insert(user)
    print(f"Inserted User ID: {user_id}")

    # Retrieve all records
    users = user_handler.fetch_all()
    print(f"All Users: {users}")

    # Clean up
    pool.close_all()


def test_create_mentions():
    pool = SQLiteConnectionPool(str((PuTi.ROOT_DIR.val / 'puti' / 'db' / 'alpha.db')), pool_size=3)
    db_manager = SQLiteManagerWithPool(pool)
    mention_handler = SQLiteModelHandlerWithPool(db_manager, Mentions)

    # Create table
    query = mention_handler.create_table()
    assert query == "CREATE TABLE IF NOT EXISTS twitter_mentions (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, author_id TEXT NOT NULL, mention_id TEXT UNIQUE, parent_id TEXT, data_time TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, replied BOOLEAN DEFAULT False, is_del BOOLEAN DEFAULT False);"


def test_add_mentions():
    pool = SQLiteConnectionPool(str((PuTi.ROOT_DIR.val / 'puti' / 'db' / 'alpha.db')), pool_size=3)
    db_manager = SQLiteManagerWithPool(pool)
    mention_handler = SQLiteModelHandlerWithPool(db_manager, Mentions)
    mentions = Mentions(
        text='obstacles',
        author_id='123',
        mention_id='4566',
        parent_id='789',
        data_time=datetime.datetime.now(),
        replied=True
    )
    mention_handler.insert(mentions)


def test_dbm():
    dbm = DBM(tb_type=Mentions)
    assert dbm


def test_dbm_tb_change():
    dbm = DBM(tb_t=Mentions)
    dbm.tb_type = UserModel
    print('')


def test_create_bot_task():
    pool = SQLiteConnectionPool(str((PuTi.ROOT_DIR.val / 'puti' / 'db' / 'alpha.db')), pool_size=3)
    dbm = SQLiteManagerWithPool(pool)
    dbh = SQLiteModelHandlerWithPool(dbm, BotTask)

    # Create table
    query = dbh.create_table()

