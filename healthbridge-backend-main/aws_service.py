import boto3
import json
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import os
from dotenv import load_dotenv

load_dotenv()

class AWSS3Manager:
    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION", "ap-southeast-1")
        self.bucket = os.getenv("AWS_S3_BUCKET", "healthbridge-orders")
        
        if self.access_key and self.secret_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
            self.enabled = True
        else:
            self.enabled = False
            print("⚠️  AWS credentials not found. S3 backup disabled.")

    def upload_order_json(self, order_data: dict, order_id: int) -> bool:
        """Upload data order sebagai JSON ke S3"""
        if not self.enabled:
            return False
        
        try:
            key = f"orders/order_{order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(order_data, indent=2),
                ContentType='application/json'
            )
            print(f"✅ Order JSON uploaded: s3://{self.bucket}/{key}")
            return True
        except Exception as e:
            print(f"❌ Error uploading order JSON: {str(e)}")
            return False

    def generate_and_upload_invoice(self, order_data: dict, order_id: int) -> bool:
        """Generate PDF invoice dan upload ke S3"""
        if not self.enabled:
            return False
        
        try:
            # Generate PDF
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
            elements = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#6366f1'),
                spaceAfter=30,
                alignment=1  # Center
            )
            
            # Title
            elements.append(Paragraph("INVOICE PEMBELIAN", title_style))
            elements.append(Spacer(1, 0.3 * inch))
            
            # Order info
            info_data = [
                ['Order ID:', f"#{order_id}"],
                ['Tanggal:', order_data.get('created_at', 'N/A')],
                ['Nama Customer:', order_data.get('customer_name', 'N/A')],
                ['Email:', order_data.get('email', 'N/A')],
                ['Phone:', order_data.get('phone', 'N/A')],
                ['Alamat:', order_data.get('address', 'N/A')],
            ]
            
            info_table = Table(info_data, colWidths=[1.5*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 0.3 * inch))
            
            # Items table
            items = order_data.get('items', [])
            items_data = [['Produk', 'Qty', 'Harga', 'Subtotal']]
            
            for item in items:
                items_data.append([
                    item.get('name', 'N/A'),
                    str(item.get('quantity', 0)),
                    f"Rp {item.get('price', 0):,.0f}",
                    f"Rp {item.get('subtotal', 0):,.0f}"
                ])
            
            items_table = Table(items_data, colWidths=[2.5*inch, 0.8*inch, 1.2*inch, 1.5*inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(items_table)
            elements.append(Spacer(1, 0.2 * inch))
            
            # Total
            total_style = ParagraphStyle(
                'TotalStyle',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#6366f1'),
                alignment=2  # Right
            )
            total_text = f"TOTAL: Rp {order_data.get('total_price', 0):,.0f}"
            elements.append(Paragraph(total_text, total_style))
            
            # Build PDF
            doc.build(elements)
            pdf_buffer.seek(0)
            
            # Upload ke S3
            key = f"invoices/invoice_{order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=pdf_buffer.getvalue(),
                ContentType='application/pdf'
            )
            print(f"✅ Invoice PDF uploaded: s3://{self.bucket}/{key}")
            return True
        except Exception as e:
            print(f"❌ Error generating invoice: {str(e)}")
            return False

    def backup_product_images(self, medicines_list: list) -> bool:
        """Backup gambar produk ke S3"""
        if not self.enabled:
            return False
        
        try:
            for medicine in medicines_list:
                if medicine.get('image_url'):
                    # Download dari local
                    local_path = f"static/images/{medicine['image_url']}"
                    if os.path.exists(local_path):
                        with open(local_path, 'rb') as f:
                            key = f"product_images/{medicine['image_url']}"
                            self.s3_client.put_object(
                                Bucket=self.bucket,
                                Key=key,
                                Body=f.read(),
                                ContentType='image/jpeg'
                            )
            print(f"✅ Product images backed up to S3")
            return True
        except Exception as e:
            print(f"❌ Error backing up images: {str(e)}")
            return False


# Initialize S3 Manager
s3_manager = AWSS3Manager()
