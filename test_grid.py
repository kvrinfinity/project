from pymongo import MongoClient
from gridfs import GridFS

client = MongoClient()
db = client.test
fs = GridFS(db)

print("GridFS is working correctly.")
