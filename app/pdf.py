"""PDF Generator for Mavuno Digital Receipts."""
import io
import time
from reportlab.lib.pagesizes import A6
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def generate_receipt_pdf(data: dict) -> bytes:
    """Generates a professional A6 digital receipt as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A6, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("<b>MAVUNO PROTOCOL</b>", styles['Title']))
    elements.append(Paragraph("Digital Proof of Sourcing", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Transaction Info
    info_data = [
        ["Receipt ID:", data['payment_id']],
        ["Date:", time.strftime('%Y-%m-%d %H:%M', time.localtime(data['settled_at'] or data['created_at']))],
        ["Buyer ID:", data['buyer_id']],
        ["Farm ID:", data['farm_id']],
        ["Method:", data['method'].upper()],
        ["Status:", data['status'].upper()],
    ]
    
    t = Table(info_data, colWidths=[60, 100])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 16))

    # Amount
    amt_style = styles['Heading2']
    amt_style.alignment = 1 # Center
    elements.append(Paragraph(f"TOTAL SETTLED", styles['Normal']))
    elements.append(Paragraph(f"<b>UGX {data['amount_ugx']:,}</b>", amt_style))
    elements.append(Spacer(1, 24))

    # Trust Signature (HMAC)
    elements.append(Paragraph("<b>SECURE LEDGER SIGNATURE</b>", styles['Normal']))
    p_style = styles['Code']
    p_style.fontSize = 6
    p_style.wordWrap = 'CJK'
    elements.append(Paragraph(data['sig'], p_style))
    
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<font color='grey' size='7'>This receipt is cryptographically verifiable via the Mavuno Ledger. Verified Ugandan Agriculture.</font>", styles['Normal']))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
