from pymongo import MongoClient

MONGO_URI = "mongodb+srv://Om:Om12345@insurance-cluster.sferbsj.mongodb.net/?appName=insurance-cluster"
client = MongoClient(MONGO_URI)

db = client["insurance_portal"]

agents_collection = db["agents"]
policies_collection = db["policies"]

icici_quotes = db["icici_quotes"]
new_india_quotes = db["new_india_quotes"]
tata_quotes = db["tata_aig_quotes"]

icici_policies = db["icici_policies"]
new_india_policies = db["new_india_policies"]
tata_policies = db["tata_aig_policies"]
