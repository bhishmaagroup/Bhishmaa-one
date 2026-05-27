import io
import base64
import barcode
from barcode.writer import ImageWriter
import qrcode


def generate_barcode_base64(value):
    """
    Generates a CODE128 barcode as a base64 encoded PNG string.
    """
    if not value:
        return ""
    try:
        code128 = barcode.get_barcode_class('code128')
        fp = io.BytesIO()
        # Write barcode PNG to bytes stream
        # ImageWriter will output a PNG image
        barcode_instance = code128(value, writer=ImageWriter())
        # Disable full text rendering under the barcode to keep sticker prints clean
        barcode_instance.write(fp, options={"write_text": True, "text_distance": 2.0, "font_size": 8})
        
        raw_bytes = fp.getvalue()
        return base64.b64encode(raw_bytes).decode('utf-8')
    except Exception as e:
        print(f"Barcode generation error: {e}")
        return ""


def generate_qrcode_base64(value):
    """
    Generates a QR code as a base64 encoded PNG string.
    """
    if not value:
        return ""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(value)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        fp = io.BytesIO()
        img.save(fp, format="PNG")
        raw_bytes = fp.getvalue()
        return base64.b64encode(raw_bytes).decode('utf-8')
    except Exception as e:
        print(f"QR code generation error: {e}")
        return ""
