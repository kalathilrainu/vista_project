import io
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
import os

def generate_token_image(visit):
    """
    Generates a JPEG image of the token for the visitor to download.
    """
    # Create a blank white image
    width = 600
    height = 800 # Portrait aspect ratio for mobile
    img = Image.new('RGB', (width, height), color='white')
    d = ImageDraw.Draw(img)
    
    # Fonts - Try to load system fonts or fallback to default
    try:
        # Assuming Windows/Standard paths or project static fonts. 
        # Using simple adjustments for now.
        title_font = ImageFont.truetype("arial.ttf", 40)
        header_font = ImageFont.truetype("arial.ttf", 30)
        token_label_font = ImageFont.truetype("arial.ttf", 25)
        token_font = ImageFont.truetype("arial.ttf", 80)
        detail_font = ImageFont.truetype("arial.ttf", 25)
        footer_font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        # Fallback if arial not found
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        token_label_font = ImageFont.load_default()
        token_font = ImageFont.load_default()
        detail_font = ImageFont.load_default()
        footer_font = ImageFont.load_default()

    # --- Draw Content ---
    
    # 1. Header (Government / VISTA)
    # Centers
    cw = width // 2
    
    d.text((cw, 50), "Village Integrated Service &", font=header_font, fill='darkgreen', anchor="mm")
    d.text((cw, 90), "Transaction Application", font=header_font, fill='darkgreen', anchor="mm")
    
    # Office Name
    office_name = visit.office.name if visit.office else "Village Office"
    d.text((cw, 140), office_name, font=title_font, fill='black', anchor="mm")
    
    # Separator
    d.line([(50, 170), (width-50, 170)], fill="gray", width=2)
    
    # 2. Token Info
    d.text((cw, 230), "Your Token Number", font=token_label_font, fill='gray', anchor="mm")
    
    # Token display
    token_text = f"{visit.token}"
    d.text((cw, 300), token_text, font=token_font, fill='black', anchor="mm")
    
    # 3. Visit Details
    # Box background
    box_top = 380
    box_bottom = 650
    d.rectangle([(50, box_top), (width-50, box_bottom)], outline="lightgray", width=2)
    
    start_y = 420
    gap = 50
    
    # Name
    d.text((70, start_y), f"Visitor: {visit.name}", font=detail_font, fill='black')
    
    # Mobile
    mobile = visit.mobile if visit.mobile else "N/A"
    d.text((70, start_y + gap), f"Mobile: {mobile}", font=detail_font, fill='black')
    
    # Purpose
    purpose = visit.purpose.name if visit.purpose else "General"
    d.text((70, start_y + gap*2), f"Purpose: {purpose}", font=detail_font, fill='black')
    
    # Time
    time_str = visit.token_issue_time.strftime("%d-%m-%Y %I:%M %p")
    d.text((70, start_y + gap*3), f"Time: {time_str}", font=detail_font, fill='black')
    
    # 4. Footer
    d.text((cw, 720), "Please wait for your number.", font=footer_font, fill='red', anchor="mm")
    d.text((cw, 750), "Thank you for visiting.", font=footer_font, fill='gray', anchor="mm")
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    buffer.seek(0)
    
    return buffer
