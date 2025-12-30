import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os

class VendorReceiptGenerator:
    def __init__(self, receipt_data):
        self.receipt_data = receipt_data
    
    def generate_pdf(self):
        """Generate PDF receipt with enhanced design"""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.gray,
            spaceAfter=30
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            leading=14
        )
        
        bold_style = ParagraphStyle(
            'CustomBold',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
            leading=14
        )
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.gray,
            spaceBefore=20
        )
        
        # Build story
        story = []
        
        # Header with logo placeholder
        header_table_data = [
            [Paragraph("Vendor Payment Receipt", title_style), ""],
            [Paragraph("Official Transaction Document", subtitle_style), ""]
        ]
        
        header_table = Table(header_table_data, colWidths=[4*inch, 2*inch])
        header_table.setStyle(TableStyle([
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(header_table)
        
        # Divider line
        story.append(Spacer(1, 0.1*inch))
        story.append(self._create_divider())
        
        # Receipt Info
        info_data = [
            [
                Paragraph(f"<b>Receipt No:</b> {self.receipt_data['receipt_number']}", normal_style),
                Paragraph(f"<b>Date & Time:</b> {self.receipt_data['date']}", normal_style)
            ]
        ]
        
        info_table = Table(info_data, colWidths=[3*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Sender Details
        story.append(Paragraph("Sender Information", heading_style))
        
        sender_data = [
            ['Name:', self.receipt_data['user']['name']],
            ['Phone:', self.receipt_data['user']['phone']],
            ['Email:', self.receipt_data['user']['email']]
        ]
        
        sender_table = Table(sender_data, colWidths=[1.5*inch, 4.5*inch])
        sender_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(sender_table)
        
        # Recipient Details
        story.append(Paragraph("Recipient Information", heading_style))
        
        recipient_data = [
            ['Name:', self.receipt_data['recipient']['name']],
            ['Account No:', self.receipt_data['recipient']['account']],
            ['IFSC Code:', self.receipt_data['recipient']['ifsc']],
            ['Bank Reference:', self.receipt_data['recipient']['bank_ref']]
        ]
        
        recipient_table = Table(recipient_data, colWidths=[1.5*inch, 4.5*inch])
        recipient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(recipient_table)
        
        # Amount Details
        story.append(Paragraph("Payment Summary", heading_style))
        
        amount_details = self.receipt_data['amount_details']
        amount_data = [
            ['Description', 'Amount (₹)'],
            ['Transfer Amount', f"{amount_details['transfer_amount']:,.2f}"],
            ['Processing Fee', f"{amount_details['processing_fee']:,.2f}"],
            ['GST @18%', f"{amount_details['gst']:,.2f}"],
            ['', ''],
            ['<b>TOTAL DEDUCTED</b>', f"<b>₹{amount_details['total_deducted']:,.2f}</b>"]
        ]
        
        amount_table = Table(amount_data, colWidths=[3.5*inch, 2.5*inch])
        amount_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f5f9')),
        ]))
        story.append(amount_table)
        
        # Transaction Details
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Transaction Information", heading_style))
        
        transaction_data = [
            ['Transaction ID:', self.receipt_data['transaction']['id']],
            ['EKO TID:', self.receipt_data['transaction']['eko_tid']],
            ['Payment Mode:', self.receipt_data['transaction']['mode']],
            ['Purpose:', self.receipt_data['transaction']['purpose']],
            ['Status:', Paragraph(f"<font color='green'><b>{self.receipt_data['transaction']['status'].upper()}</b></font>", normal_style)]
        ]
        
        transaction_table = Table(transaction_data, colWidths=[2*inch, 4*inch])
        transaction_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(transaction_table)
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        story.append(self._create_divider())
        story.append(Spacer(1, 0.2*inch))
        
        footer_text = [
            Paragraph("This is a computer generated receipt. No signature required.", footer_style),
            Paragraph("Thank you for using our services.", footer_style),
            Paragraph(f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", footer_style)
        ]
        
        for text in footer_text:
            story.append(text)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _create_divider(self):
        """Create a horizontal divider"""
        data = [['']]
        table = Table(data, colWidths=[6*inch], rowHeights=[2])
        table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ]))
        return table