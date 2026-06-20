from app.db import mongo_client

class DummyClient:
    def __init__(self, uri):
        self.uri = uri
        self.closed = False

    def __getitem__(self, name):
        return DummyDatabase(name)

    def close(self):
        self.closed = True

class DummyDatabase:
    def __init__(self, name):
        self.name = name

    def __getitem__(self, collection_name):
        return {"collection": collection_name}

def test_connect_uses_default_uri(monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.setattr(mongo_client, "MongoClient", DummyClient)
    db = mongo_client.MongoDB()

    db.connect()

    assert db.client.uri == "mongodb://localhost:27017"
    assert db.db.name == "quiz_app"

def test_connect_uses_env_uri(monkeypatch):
    monkeypatch.setattr(mongo_client, "MongoClient", DummyClient)
    db = mongo_client.MongoDB()

    db.connect()

    assert db.client.uri == "mongodb://localhost:27017"

def test_close_closes_client(monkeypatch):
    monkeypatch.setattr(mongo_client, "MongoClient", DummyClient)
    db = mongo_client.MongoDB()
    db.connect()

    db.close()

    assert db.client.closed is True

def test_close_without_client_is_safe():
    db = mongo_client.MongoDB()

    db.close()

    assert db.client is None

def test_quizzes_and_results_properties(monkeypatch):
    monkeypatch.setattr(mongo_client, "MongoClient", DummyClient)
    db = mongo_client.MongoDB()
    db.connect()

    assert db.quizzes == {"collection": "quizzes"}
    assert db.results == {"collection": "results"}
