import os
from PIL import Image, ImageDraw, ImageFont

NAVY = (11, 19, 43)
BLUE = (37, 99, 235)
GOLD = (255, 199, 44)
LIGHT_BLUE = (240, 245, 250)
WHITE = (255, 255, 255)
GRAY = (110, 120, 140)
DARK_GRAY = (14, 22, 48)

def rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)

def main():
    width, height = 1280, 720
    img = Image.new('RGB', (width, height), NAVY)
    draw = ImageDraw.Draw(img)
    nav_h = 48
    rounded_rect(draw, (0, 0, width, nav_h), 6, DARK_GRAY)
    rounded_rect(draw, (16, 8, 184, 40), 6, BLUE)
    draw.text((32, 12), 'EchoMind', fill=WHITE)
    draw.text((228, 14), 'Dashboard', fill=GOLD)
    draw.text((368, 14), 'Chat', fill=WHITE)
    draw.text((448, 14), 'History', fill=(180, 190, 210))
    draw.text((628, 14), 'Settings', fill=(180, 190, 210))

    rounded_rect(draw, (0, nav_h, 212, height), 10, (14, 22, 48))
    sidebar_items = ['Ask AI', 'Transcripts', 'Notes', 'Tools', 'Integrations']
    for idx, item in enumerate(sidebar_items):
        y = nav_h + 20 + idx * 56
        if idx == 0:
            rounded_rect(draw, (14, y, 200, y + 44), 6, BLUE)
            draw.text((30, y + 12), item, fill=WHITE)
        else:
            draw.ellipse((36, y + 16, 48, y + 28), fill=GOLD)
            draw.text((58, y + 12), item, fill=(180, 190, 210))

    rounded_rect(draw, (228, nav_h + 18, width - 6, height - 6), 6, LIGHT_BLUE)
    draw.text((260, nav_h + 32), 'Working session', fill=DARK_GRAY)
    draw.text((260, nav_h + 62), 'Your AI co-pilot is live.', fill=(40, 55, 80))

    card_w, card_h = 206, 108
    gap = 18
    cards = [('Response latency','1.7 s'),('Tokens saved','18.4k'),('Tasks completed','122')]
    for i, (label, value) in enumerate(cards):
        x = 260 + i * (card_w + gap)
        rounded_rect(draw, (x, nav_h + 112, x + card_w, nav_h + 220), 6, WHITE)
        draw.text((x + 16, nav_h + 128), label, fill=GRAY)
        draw.text((x + 16, nav_h + 158), value, fill=NAVY)
        draw.rounded_rectangle((x + 16, nav_h + 190, x + card_w - 16, nav_h + 192), 6, BLUE)

    right_x, right_y = 989, nav_h + 26
    panel_w, panel_h = 226, 428
    rounded_rect(draw, (right_x, right_y, right_x + panel_w, right_y + panel_h), 6, WHITE)
    draw.text((right_x + 16, right_y + 16), 'Copilot', fill=NAVY)
    messages = [
        ('You', 'Summarize meeting'),
        ('AI', '3 key actions + owners'),
        ('You', 'Draft follow-up email'),
        ('AI', 'Drafted in sidebar'),
    ]
    for i, (who, text) in enumerate(messages):
        y = right_y + 56 + i * 52
        if who == 'You':
            rounded_rect(draw, (right_x + 14, y, right_x + 200, y + 26), 10, LIGHT_BLUE)
            draw.text((right_x + 22, y + 6), text, fill=NAVY)
        else:
            rounded_rect(draw, (right_x + 14, y, right_x + 200, y + 36), 10, NAVY)
            draw.text((right_x + 22, y + 10), text, fill=WHITE)

    rounded_rect(draw, (228, height - 134, width - 6, height - 16), 6, WHITE)
    draw.text((258, height - 116), 'Live transcript', fill=NAVY)
    draw.text((258, height - 90), '00:03:12  |  Active speaker: Jordan', fill=GRAY)
    rounded_rect(draw, (738, height - 108, 1120, height - 84), 6, LIGHT_BLUE)
    draw.text((756, height - 104), 'Ask AI about the last 3 minutes', fill=BLUE)

    rounded_rect(draw, (1088, nav_h + 10, 1200, nav_h + 38), 13, (56, 189, 248))
    draw.text((1106, nav_h + 16), '● Live', fill=WHITE)
    return img

if __name__ == '__main__':
    out = '/g/hermes-files/real-time-ai-copilot/assets/docs/screenshot.png'
    img = main()
    img.save(out)
    print('Saved', out)
