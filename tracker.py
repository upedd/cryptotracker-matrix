import adafruit_display_text.label
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
import time
import requests

symbol = "BTC"  # Change this for different coins

displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64,
    height=32,
    bit_depth=2,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13,
    latch_pin=board.D0,
    output_enable_pin=board.D1,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

main_group = displayio.Group()

text_group = displayio.Group()
price_label = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0xFFFFFF,
    text="Loading...",
    x=0,
    y=6
)
percent_label = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0xFFFFFF,
    text="",
    x=0,
    y=6
)
text_group.append(price_label)
text_group.append(percent_label)

text_group2 = displayio.Group()
price_label2 = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0xFFFFFF,
    text="",
    x=0,
    y=6
)
percent_label2 = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0xFFFFFF,
    text="",
    x=0,
    y=6
)
text_group2.append(price_label2)
text_group2.append(percent_label2)

graph_bitmap = displayio.Bitmap(64, 16, 3)
graph_palette = displayio.Palette(3)
graph_palette[0] = 0x000000 
graph_palette[1] = 0x00FF00 
graph_palette[2] = 0xFF0000

graph_group = displayio.Group(scale=1, x=0, y=16)
graph_tile = displayio.TileGrid(graph_bitmap, pixel_shader=graph_palette)
graph_group.append(graph_tile)

main_group.append(graph_group)
main_group.append(text_group)
main_group.append(text_group2)
display.root_group = main_group

def get_crypto_data(coin="bitcoin"):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
        params = {"vs_currency": "usd", "days": "1"}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if "prices" not in data or len(data["prices"]) < 1:
            raise ValueError("No price data available")
            
        prices = [point[1] for point in data["prices"]]
        current_price = prices[-1]
        percent_change = ((current_price - prices[0]) / prices[0]) * 100
        
        return current_price, percent_change, prices
        
    except Exception as e:
        print(f"API Error: {str(e)}")
        return None, None, None

def update_text_labels(price, change):
    price_text = f"{symbol}: ${price:.1f} "
    percent_text = f"{change:+.1f}%"
    percent_color = 0x00FF00 if change >= 0 else 0xFF0000
    
    price_label.text = price_text
    percent_label.text = percent_text
    percent_label.color = percent_color
    
    price_width = price_label.bounding_box[2]
    percent_label.x = price_width
    
    price_label2.text = price_text
    percent_label2.text = percent_text
    percent_label2.color = percent_color
    percent_label2.x = price_width
    
    return price_width + percent_label.bounding_box[2]

def draw_graph(prices):
    graph_bitmap.fill(0)
    if not prices:
        return
        
    max_price = max(prices)
    min_price = min(prices)
    price_range = max_price - min_price or 1
    
    for x, price in enumerate(prices[-64:]):
        y = 15 - int(15 * (price - min_price) / price_range)
        y = max(0, min(15, y))
        
        color = 1 if x == 0 or price > prices[x-1] else 2
        graph_bitmap[x % 64, y] = color

last_update = 0
update_interval = 300
current_data = (None, None, None)
text_width = 0
scroll_pos = 0

while True:
    try:
        if time.monotonic() - last_update > update_interval:
            current_data = get_crypto_data()
            last_update = time.monotonic()
            
            if None in current_data:
                raise ValueError("Invalid data received")
            
            price, change, history = current_data
            text_width = update_text_labels(price, change)
            scroll_pos = 0
            
            text_group.x = 0
            text_group2.x = text_width + 2
            
        scroll_pos -= 1
        text_group.x = scroll_pos
        text_group2.x = scroll_pos + text_width + 2
        
        if scroll_pos < -text_width * 2:
            scroll_pos = 0
            
        draw_graph(current_data[2])
        
        display.refresh()
        
    except Exception as e:
        print("Error:", e)
        price_label.text = "Error"
        percent_label.text = "Retrying..."
        text_group2.x = -100
        display.refresh()
        time.sleep(10)
        continue
    
    time.sleep(0.05)