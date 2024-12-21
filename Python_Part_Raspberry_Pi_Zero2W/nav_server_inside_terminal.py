import bluetooth
import logging
import time
from datetime import datetime
import base64
import io
from PIL import Image
import numpy as np

# Configure logging with date and time format
#logging.basicConfig(
#    level=logging.DEBUG,
#    format='%(asctime)s - %(levelname)s - %(message)s',
#    datefmt='%Y-%m-%d %H:%M:%S'
#)
#logger = logging.getLogger('BtServer')

def parse_maps_notification(notification_text):
    """
    Parse a Maps notification text into separate components.
    
    Args:
        notification_text (str): Raw notification text containing title, text, subtext and icon
        
    Returns:
        dict: Dictionary containing parsed components
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

def base64_to_ascii_art(base64_string, width=100, ascii_chars=" .:-=+*#%@"):
    """
    Convert a base64 encoded PNG image to ASCII art.
    
    Args:
        base64_string (str): Base64 encoded PNG image string
        width (int): Desired width of ASCII art output
        ascii_chars (str): Characters to use for ASCII art (from darkest to lightest)
        
    Returns:
        str: ASCII art representation of the image
    """
    # Decode base64 string to image
    image_data = base64.b64decode(base64_string)
    image = Image.open(io.BytesIO(image_data))
    
    # Convert to grayscale
    image = image.convert('L')
    
    # Calculate new height to maintain aspect ratio
    aspect_ratio = image.height / image.width
    height = int(width * aspect_ratio * 0.5)  # * 0.5 to account for terminal character spacing
    
    # Resize image
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    
    # Convert image to numpy array
    pixels = np.array(image)
    
    # Normalize pixel values to index into ascii_chars
    normalized_pixels = ((pixels - pixels.min()) * (len(ascii_chars) - 1) / 
                        (pixels.max() - pixels.min())).astype(int)
    
    # Convert pixels to ASCII characters
    ascii_art = []
    for row in normalized_pixels:
        ascii_row = ''.join(ascii_chars[pixel] for pixel in row)
        ascii_art.append(ascii_row)
    
    return '\n'.join(ascii_art)

def print_maps_notification(notification):
    parsed = parse_maps_notification(notification)
    msg = ""
    if(parsed["title"] != ""):
        msg += parsed["title"] + "\n"

    if(parsed["text"] != ""):
        msg += parsed["text"] + "\n"

    if(parsed["subText"] != ""):
        msg += parsed["subText"] + "\n"

    if(parsed["largeIconBase64"] != ""):
        msg += base64_to_ascii_art(parsed["largeIconBase64"], width=60, ascii_chars=" .") + "\n"

    if(msg != ""):
        print(f"{msg}\n")

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
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    port = 1
    server_sock.bind(("", port))
    server_sock.listen(1)
    
    print(f"Listening on RFCOMM port {port}")
    
    while True:
        try:
            client_sock, client_info = server_sock.accept()
            print(f"Accepted connection from {client_info}")
            
            while True:
                try:
                    message = receive_full_message(client_sock)
                    if not message:
                        break
#                    logger.info(f"Received: {message}\n")

                    print_maps_notification(message)
                    
                    # Send response
                    if message == "PING":
                        response = "PONG\n"
                    else:
                        response = "OK\n"
                    client_sock.send(response.encode())
                    
                except Exception as e:
                    print(f"Error: {e}")
                    break
                    
            client_sock.close()
            print("Connection closed")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
            
    server_sock.close()
    print("Server stopped")

if __name__ == "__main__":
    main()
