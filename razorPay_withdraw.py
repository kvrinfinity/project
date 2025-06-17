import razorpay

client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_KEY_SECRET"))

payout = client.payout.create({
  "account_number": "232323XXXXXX",  # Your virtual account number
  "fund_account": {
    "account_type": "vpa",
    "vpa": {
      "address": "8106147247@upi"
    },
    "contact": {
      "name": "Kumbhakonam Praveen",
      "type": "Student",
      "email": "kumbakonampraveen@gmail.com",
      "contact": "8106147247"
    }
  },
  "amount": 1000,  # in paise => ₹1000
  "currency": "INR",
  "mode": "UPI",
  "purpose": "cashback",
  "queue_if_low_balance": True
})
