from pymongo import MongoClient

uri = "mongodb+srv://nishankamath:kvrinfinity@kvr-test.hax50hy.mongodb.net/?retryWrites=true&w=majority&appName=kvr-testZ"

client = MongoClient(uri)
db = client['company']
collection = db['users']

# Insert sample data
collection.insert_one({"name": "Nishan", "email": "nishan@example.com"})

# Retrieve data
for user in collection.find():
    print(user)
