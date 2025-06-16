from pymongo import MongoClient
from gridfs import GridFS
from datetime import datetime, timedelta
import random
import string

# MongoDB URI
uri = "mongodb+srv://praveen:tHXsIKjbFLMuwki4@cluster0.ct1utq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB
client = MongoClient(uri)
db = client['company']  # Replace with your actual DB name

# Collections
user_col = db['users']
membership_col = db['membership']
fs = GridFS(db)

# Dummy Data
fname = "Praveen"
lname = "Kumbhakonam"
email = "kumbakonampraveen@gmail.com"
password = "password"  


ref_code = 'kvr1001'

# Insert user
user_col.insert_one({
    'fname': fname,
    'lname': lname,
    'email': email,
    'password': password,
    'ref_code': ref_code,
    'enrolled_courses': []
})

# Simulate receipt upload to GridFS
receipt_content = b"This is a dummy receipt PDF content."
receipt_file_id = fs.put(receipt_content, filename="receipt.pdf")

# Membership data
user_email = email
user_name = f"{fname} {lname}"
payment_date = datetime.now()
valid_till = payment_date + timedelta(days=360)
receipt_id = "RCP" + ''.join(random.choices(string.digits, k=5))

# Insert membership
membership_col.insert_one({
    "user_email": user_email,
    "user_name": user_name,
    "payment_date": payment_date,
    "receipt_id": receipt_id,
    "valid_till": valid_till,
    "receipt_file_id": receipt_file_id
})

print("✅ Dummy user and membership inserted successfully.")
