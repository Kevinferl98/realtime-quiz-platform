import os
from pymongo import MongoClient
from my_observability import get_logger

logger = get_logger(__name__)

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None

    def connect(self):
        uri = os.environ.get("MONGO_URI",  "mongodb://localhost:27017")
        self.client = MongoClient(uri)
        self.db = self.client["quiz_app"]
        logger.info("Connected to MongoDB")

    def close(self):
        if self.client:
            self.client.close()
            logger.info("Closed connection to MongoDB")

    @property
    def quizzes(self):
        return self.db["quizzes"]

    @property
    def results(self):
        return self.db["results"]

mongo_db = MongoDB()