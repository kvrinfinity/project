from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

def generate_receipt(member_name, email, phone, amount, receipt_id):
    file_name = f"receipt_{receipt_id}.pdf"
    doc = SimpleDocTemplate(file_name, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("<b>KVR Infinity - Membership Receipt</b>", styles['Title']))
    elements.append(Spacer(1, 20))

    # Date and Receipt ID
    date_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    elements.append(Paragraph(f"Receipt ID: <b>{receipt_id}</b><br/>Date: <b>{date_str}</b>", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Table data
    data = [
        ["Field", "Details"],
        ["Name", member_name],
        ["Email", email],
        ["Phone", phone],
        ["Membership", "All Courses Access"],
        ["Amount Paid", f"₹{amount}"],
    ]

    # Table styling
    table = Table(data, hAlign='LEFT', colWidths=[150, 300])
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

    # Footer
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("✅ Thank you for becoming a premium member of <b>KVR Infinity</b>!", styles['Normal']))
    elements.append(Paragraph("This receipt is computer-generated and does not require a signature.", styles['Italic']))

    # Build PDF
    doc.build(elements)
    print(f"✅ Receipt saved as: {file_name}")

# Example usage
generate_receipt(
    member_name="Nishan Kamath",
    email="nishan@gmail.com",
    phone="+91-9380719446",
    amount=3000,
    receipt_id="KVR-20240609-001"
)
