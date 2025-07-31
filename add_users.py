import pandas as pd
import bcrypt
import random
import string
from pymongo import MongoClient
from gridfs import GridFS
from datetime import datetime, timedelta
from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# MongoDB setup
uri = "mongodb+srv://praveen:tHXsIKjbFLMuwki4@cluster0.ct1utq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB
client = MongoClient(uri)
db = client['company'] 
users_collection = db['users']
membership_collection = db['membership']

# Default password
default_password = 'password'
hashed_pw = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt())

fs = GridFS(db)

# Constants
amount = 3000
today = datetime.now()
validity = today + timedelta(days=365)
# Sample user data from the image
users = [
    ("Vibitha", "Pallath", "vibithapallath2024@gmail.com", "9495114932"),
    ("Sushmitha", "Durgam", "durgamsushmitha300@gmail.com", "8106665752"),
    ("Anjana Unnikrishnan", "unnikrishnan", "anjanaunnikrishnan7474@gmail.com", "7736387474"),
    ("Reema", "Maimoona", "reemabasheer135@gmail.com", "9481338450"),
    ("Shilpa", "R", "shilpaakku665@gmail.com", "8590028531"),
    ("Sanjana", "Mohan", "sanjanamohan3@gmail.com", "9048981482"),
    ("Anuj", "Jain", "badkulanuj23@gmail.com", "7869150941"),
    ("Minali", "Rathod", "minalirathod2021@gmail.com", "7625026620"),
    ("Jaya", "Prakash", "jayaprakash14414325@gmail.com", "8331829897"),
    ("Rajesh", "Raghunthan", "rajeshraghu77@gmail.com", "9840503597"),
    ("Reshmi", "S", "reshmi.cse.1234@gmail.com", "9518901441"),
    ("A Jacob", "selvan", "jacobselvan.a@gmail.com", "9092405555"),
    ("Amruth", "G", "amruthreddy005@gmail.com", "9047033261"),
    ("Muskan", "Singh", "smuskanofficial07@gmail.com", "8618053868"),
    ("Nidheesh", "N A", "nidheeshamin74@gmail.com", "7411390475"),
    ("Thudamaladinne", "praveena", "thudamaladinnepraveena@gmail.com", "7660052169"),
    ("Ashok", "Kumar", "ashokkumar10272006@gmail.com", "8309444165"),
    
]



def generate_receipt(member_name, email, phone, amount, receipt_id, transaction_date, valid_through):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Styles
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=14, spaceAfter=12, alignment=1)
    label_style = styles['Normal']

    # Company Info
    elements.append(Paragraph("KVR Infinity", header_style))
    elements.append(Paragraph("1st Floor, KH - Connects, JP Nagar 4th Phase, Bengaluru, India – 560078", label_style))
    elements.append(Paragraph("CIN: U72900AP2019PTC113696 | GSTIN: 37AAFCI5145J1ZD", label_style))
    elements.append(Paragraph("Phone: 918106147247 | Email: sales@kvrinfinity.in", label_style))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("PAYMENT RECEIPT", header_style))
    elements.append(Paragraph(f"<b>Receipt No:</b> {receipt_id}", label_style))
    elements.append(Paragraph(f"<b>Receipt Date:</b> {datetime.now().strftime('%Y/%m/%d')}", label_style))
    elements.append(Paragraph(f"<b>Transaction Date:</b> {transaction_date.strftime('%Y/%m/%d')}", label_style))
    elements.append(Paragraph(f"<b>Transaction Amount:</b> Rs. {amount:,.2f}", label_style))
    elements.append(Paragraph(f"<b>Valid Through:</b> {valid_through.strftime('%Y/%m/%d')}", label_style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"<b>Bill to:</b> {member_name}", label_style))
    elements.append(Paragraph(phone, label_style))
    elements.append(Paragraph(email, label_style))
    elements.append(Spacer(1, 12))

    # Item Table
    data = [["Item & Description", "Amount"], ["KVR Infinity Membership", f"Rs. {amount:,.2f}"]]
    table = Table(data, colWidths=[350, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#850014")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BOX', (0, 0), (-1, -1), 1, colors.gray),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("This is a computer generated pay receipt and does not require a signature.", styles['Italic']))
    elements.append(Paragraph("The total amount is inclusive of 18% GST.", styles['Italic']))

    doc.build(elements)
    buffer.seek(0)
    return buffer
# Function to generate a unique ref_code
def generate_unique_ref_code():
    while True:
        ref_code = 'kvr' + str(random.randint(1000, 9999))
        if not users_collection.find_one({'ref_code': ref_code}):
            return ref_code

# Inserting users into both collections
for fname, lname, email, phone in users:
    ref_code = generate_unique_ref_code()
    
    user_data = {
        "fname": fname,
        "lname": lname,
        "email": email,
        "password": hashed_pw,
        "phone": phone,
        "ref_code": ref_code,
        "enrolled_courses": []
    }
    
    user_name = f"{fname} {lname}"
    receipt_id = f"KVR-{today.strftime('%Y%m%d-%H%M%S')}-{random.randint(10,99)}"
    receipt_pdf = generate_receipt(user_name, email, phone, amount, receipt_id, today, validity)
    receipt_file_id = fs.put(receipt_pdf, filename=f"{receipt_id}.pdf")

    membership_doc = {
        "user_email": email,
        "user_name": user_name,
        "payment_date": today,
        "receipt_id": receipt_id,
        "valid_till": validity,
        "receipt_file_id": receipt_file_id
    }

    
    # Insert into 'users' collection
    users_collection.insert_one(user_data)
    
    # Insert into 'membership' collection
    membership_collection.insert_one(membership_doc)
    print(f"✅ Membership inserted: {receipt_id}")
    print(f"Inserted into both: {email}")
"""
import bcrypt
from pymongo import MongoClient

# MongoDB setup
uri = "mongodb+srv://praveen:tHXsIKjbFLMuwki4@cluster0.ct1utq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client['company']
users_collection = db['users']

# New default password
default_password = 'password'

# Fetch all users
all_users = users_collection.find()

for user in all_users:
    email = user.get('email')
    
    # Re-hash the password correctly
    hashed_pw = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt())


    # Update the user's password
    result = users_collection.update_one(
        {'_id': user['_id']},
        {'$set': {'password': hashed_pw}}
    )
    
    if result.modified_count:
        print(f"✅ Updated password for: {email}")
    else:
        print(f"⚠️ Password not updated for: {email}")
"""