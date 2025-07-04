"""
@Author: obstacle
@Time: 16/01/25 15:19
@Description:  
"""
from puti.db.base_manager import BaseManager
from puti.db.model.client.twitter import UserModel

# DBM (Database Manager) class for backward compatibility
class DBM(BaseManager):
    """
    Database Manager class for handling database operations.
    This is a wrapper around BaseManager for backward compatibility.
    """
    pass
