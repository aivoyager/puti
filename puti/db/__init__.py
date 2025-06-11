"""
@Author: obstacle
@Time: 16/01/25 15:19
@Description:  
"""
from typing import Type
from puti.db.db_sqlite import dbm_maker, SQLiteModelHandlerWithPool, SQLiteManagerWithPool, SQLiteConnectionPool
from pydantic import BaseModel, ConfigDict, Field
from puti.db.model import Model
from pathlib import Path
from puti.constant.base import PuTi
from puti.logs import logger_factory

lgr = logger_factory.default


class DBM(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    pool: SQLiteConnectionPool = Field(None, description='conn pool', validate_default=False)
    pool_size: int = Field(default=PuTi.POOL_SIZE.val)
    db_path: Path = Field(default=PuTi.ROOT_DIR.val / 'db' / 'puti.db')
    dbh: SQLiteModelHandlerWithPool = Field(None, description='database handler', validate_default=False)
    dbm: SQLiteManagerWithPool = Field(None, description='database manager', validate_default=False)

    tb: Model = None
    tb_t: Type[Model] = Field(None, description='table type', validate_default=False)

    def model_post_init(self, __context):
        if not self.tb_t:
            raise ValueError('model type `tb_t` is required')

        if not self.pool:
            self.pool = SQLiteConnectionPool(str(self.db_path), self.pool_size)
        if not self.dbm:
            self.dbm = SQLiteManagerWithPool(self.pool)
        if not self.dbh:
            self.dbh = SQLiteModelHandlerWithPool(self.dbm, self.tb_t)
        lgr.info(f'DBM initialized at {self.dbh}')

    @property
    def tb_type(self):
        return self.tb_t

    @tb_type.setter
    def tb_type(self, tb_type: Type[Model]):
        self.dbh = SQLiteModelHandlerWithPool(self.dbm, tb_type)
        self.dbh.table_name = tb_type.__table_name__
        self.tb_t = tb_type
        lgr.info(f'DBM change to {tb_type}')






