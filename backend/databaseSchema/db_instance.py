from motor.motor_asyncio import AsyncIOMotorDatabase

_db = None

def init_db(db):
    global _db
    _db = db

def get_db_instance():
    return _db