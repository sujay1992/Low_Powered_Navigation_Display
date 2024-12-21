import bluetooth
import logging
import time
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import digitalio
import board
import adafruit_rgb_display.ili9341 as ili9341

# Display dimensions
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

import bluetooth
import time
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import digitalio
import board
import adafruit_rgb_display.ili9341 as ili9341

def add_icon_to_image(base_image, base64_icon, max_icon_width=160, max_icon_height=120):
    """
    Add a base64 encoded icon to a base image within specified maximum dimensions.
    
    Args:
        base_image (PIL.Image.Image): The base 320x240 image to add the icon to
        base64_icon (str): Base64 encoded icon image
        max_icon_width (int): Maximum width for the icon (default 160)
        max_icon_height (int): Maximum height for the icon (default 120)
    
    Returns:
        PIL.Image.Image: Image with the icon added
    """
    try:
        # Decode base64 icon
        icon_data = base64.b64decode(base64_icon)
        
        # Open the icon image
        original_icon = Image.open(BytesIO(icon_data))
        
        # Calculate scaling while maintaining aspect ratio
        original_ratio = original_icon.width / original_icon.height
        target_ratio = max_icon_width / max_icon_height
        
        if original_ratio > target_ratio:
            # Icon is wider relative to target, so scale by width
            new_width = max_icon_width
            new_height = int(max_icon_width / original_ratio)
        else:
            # Icon is taller relative to target, so scale by height
            new_height = max_icon_height
            new_width = int(max_icon_height * original_ratio)
        
        # Resize the icon
        resized_icon = original_icon.resize((new_width, new_height), Image.LANCZOS)
        
        # Calculate position to center the icon in the 160x120 area
        # The 160x120 area is positioned in the bottom right of the 320x240 image
        #x_offset = 320 - max_icon_width + (max_icon_width - new_width) // 2
        #y_offset = 240 - max_icon_height + (max_icon_height - new_height) // 2
        x_offset = 200
        y_offset = 10

        # Paste the icon onto the base image
        # Use the icon's alpha channel for transparency if it exists
        base_image.paste(resized_icon, (x_offset, y_offset), 
                         resized_icon if resized_icon.mode == 'RGBA' else None)
        
        return base_image
    
    except Exception as e:
        print(f"Error adding icon: {e}")
        return base_image

def display_maps_notification(display, notification):
    parsed = parse_maps_notification(notification)
    
    # Create image with original dimensions
    image = Image.new("RGB", (320, 240))  # Original dimensions
    print("Image dimensions:", image.size)
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("/usr/share/fonts/ttf-dejavu/DejaVuSans.ttf", 24)
        small_font = ImageFont.truetype("/usr/share/fonts/ttf-dejavu/DejaVuSans.ttf", 20)
        big_font = ImageFont.truetype("/usr/share/fonts/ttf-dejavu/DejaVuSans.ttf", 30)

    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        big_font = ImageFont.load_default()

    # Black background
    draw.rectangle((0, 0, 319, 239), fill=(0, 0, 0))

    x = 10  # Offset to avoid scrambled area
    y = 10  # Start near top

    if parsed["title"]:
        draw.text((x, y), parsed["title"], font=big_font, fill=(0, 0, 255))
    
    y += 30

    if parsed["text"]:
        words = parsed["text"].split()
        lines = []
        current_line = []
        max_width = 199
        
        for word in words:
            current_line.append(word)
            test_line = " ".join(current_line)
            w, h = draw.textsize(test_line, font=small_font)
            if w > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []
        
        if current_line:
            lines.append(" ".join(current_line))
        
        for line in lines:
            if y < 220:
                draw.text((x, y), line, font=small_font, fill=(255, 255, 255))
                y += 20

    y = 180
    if parsed["subText"] and y < 220:
        #y += 10
        #draw.text((x, y), parsed["subText"], font=font, fill=(0, 255, 255))
        words = parsed["subText"].split()
        lines = []
        current_line = []
        max_width = 300
        
        for word in words:
            current_line.append(word)
            test_line = " ".join(current_line)
            w, h = draw.textsize(test_line, font=font)
            if w > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []
        
        if current_line:
            lines.append(" ".join(current_line))
        
        for line in lines:
            if y < 220:
                draw.text((x, y), line, font=font, fill=(0, 255, 255))
                y += 20

    if parsed["largeIconBase64"]:
        #print(parsed["largeIconBase64"])
        image = add_icon_to_image(image, parsed["largeIconBase64"])

    print("Sending to display...")
    # Transpose the image to correct orientation
    image = image.transpose(Image.Transpose.ROTATE_90)
    display.image(image)
    print("Display update complete")

def init_display():
    cs_pin = digitalio.DigitalInOut(board.CE0)
    dc_pin = digitalio.DigitalInOut(board.D25)
    reset_pin = digitalio.DigitalInOut(board.D24)

    spi = board.SPI()

    display = ili9341.ILI9341(
        spi,
        rotation=90,
        cs=cs_pin,
        dc=dc_pin,
        rst=reset_pin,
        baudrate=24000000,
        width=320,    # Back to original
        height=240    # Back to original
    )
    
    print("Display dimensions:", display.width, "x", display.height)
    return display

def parse_maps_notification(notification_text):
    """
    Parse a Maps notification text into separate components.
    """
    # Initialize variables
    title = ""
    text = ""
    subText = ""
    largeIconBase64 = ""
    
    # Split the input text into lines
    lines = notification_text.split('\n')
    
    current_section = None
    
    for line in lines:
        if line.startswith("Maps Notification:"):
            continue
        elif line.startswith("Title: "):
            current_section = "title"
            title = line.replace("Title: ", "")
        elif line.startswith("Text: "):
            current_section = "text"
            text = line.replace("Text: ", "")
        elif line.startswith("SubText: "):
            current_section = "subtext"
            subText = line.replace("SubText: ", "")
        elif line.startswith("LargeIconBase64: "):
            current_section = "icon"
            largeIconBase64 = line.replace("LargeIconBase64: ", "")
        elif line.strip() and current_section == "icon":
            largeIconBase64 += line.strip()
            
    return {
        "title": title,
        "text": text,
        "subText": subText,
        "largeIconBase64": largeIconBase64
    }

def receive_full_message(sock):
    data = sock.recv(4096)
    if not data:
        return ""

    message = data.decode()

    # If this is a simple message without <<<END>>>, return it directly
    if "LargeIconBase64" not in message:
        return message.strip()

    message_parts = [message]
    while True:
        # Check if we've received the end marker
        if "<<<END>>>" in message:
            break
        
        data = sock.recv(4096)
        if not data:
            break

        message = data.decode()
        message_parts.append(message)
    
    # Combine all parts and remove the end marker
    full_message = "".join(message_parts)
    return full_message.replace("<<<END>>>", "").strip()

def main():
    # Initialize display
    display = init_display()
    
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    port = 1
    server_sock.bind(("", port))
    server_sock.listen(1)
    
    print(f"Listening on RFCOMM port {port}")
    display_maps_notification(display, "Maps Notification:\nText: Waiting for connection...")
    
    while True:
        try:
            client_sock, client_info = server_sock.accept()
            print(f"Accepted connection from {client_info}")
            display_maps_notification(display, 
                f"Maps Notification:\nTitle: Connected\nText: {client_info}")
            
            while True:
                try:
                    message = receive_full_message(client_sock)
                    if not message:
                        break

                    # Display notification on LCD
                    display_maps_notification(display, message)
                    
                    # Send response
                    client_sock.send("OK\n".encode())
                    
                except Exception as e:
                    print(f"Error: {e}")
                    display_maps_notification(display, 
                        f"Maps Notification:\nTitle: Error\nText: {str(e)}")
                    break
                    
            client_sock.close()
            print("Connection closed")
            display_maps_notification(display, 
                "Maps Notification:\nTitle: Connection closed\nText: Waiting for connection...")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            display_maps_notification(display, 
                f"Maps Notification:\nTitle: Error\nText: {str(e)}")
            time.sleep(1)
            
    server_sock.close()
    print("Server stopped")
    display_maps_notification(display, "Maps Notification:\nTitle: Server stopped")

if __name__ == "__main__":
    main()