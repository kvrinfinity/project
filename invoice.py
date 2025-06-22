from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime

def generate_receipt(member_name, email, phone, amount, receipt_id, transaction_date, valid_through):
    file_name = f"receipt_{receipt_id}.pdf"
    doc = SimpleDocTemplate(file_name, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Custom Styles
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=14, spaceAfter=12, alignment=1)
    label_style = styles['Normal']
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')

    # Company Info
    elements.append(Paragraph("KVR Infinity", header_style))
    elements.append(Paragraph("1st Floor, KH - Connects, JP Nagar 4th Phase, Bengaluru, India – 560078", label_style))
    elements.append(Paragraph("CIN: U72900AP2019PTC113696 | GSTIN: 37AAFCI5145J1ZD", label_style))
    elements.append(Paragraph("Phone: 918106147247 | Email: sales@kvrinfinity.in", label_style))
    elements.append(Spacer(1, 20))

    # Title
    elements.append(Paragraph("PAYMENT RECEIPT", header_style))

    # Receipt Metadata
    elements.append(Paragraph(f"<b>Receipt No:</b> {receipt_id}", label_style))
    elements.append(Paragraph(f"<b>Receipt Date:</b> {datetime.now().strftime('%Y/%m/%d')}", label_style))
    elements.append(Paragraph(f"<b>Transaction Date:</b> {transaction_date}", label_style))
    elements.append(Paragraph(f"<b>Transaction Amount:</b> Rs. {amount:,.2f}", label_style))
    elements.append(Paragraph(f"<b>Valid Through:</b> {valid_through}", label_style))
    elements.append(Spacer(1, 12))

    # Bill To
    elements.append(Paragraph(f"<b>Bill to:</b> {member_name}", label_style))
    elements.append(Paragraph(phone, label_style))
    elements.append(Paragraph(email, label_style))
    elements.append(Spacer(1, 12))

    # Item Table
    data = [
        ["Item & Description", "Amount"],
        ["KVR Infinity Membership", f"Rs. {amount:,.2f}"]
    ]
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

    # Notes
    elements.append(Paragraph("This is a computer generated pay receipt and does not require a signature.", styles['Italic']))
    elements.append(Paragraph("The total amount is inclusive of 18% GST.", styles['Italic']))

    doc.build(elements)
    print(f"✅ Receipt saved as: {file_name}")

generate_receipt(
    member_name="Poornima Poornima",
    email="47poornima@gmail.com",
    phone="918179552589",
    amount=21000,
    receipt_id="KVRIAS-ST-A0030",
    transaction_date="2025/03/12",
    valid_through="2027/12/31"
)
