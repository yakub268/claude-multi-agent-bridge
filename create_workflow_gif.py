#!/usr/bin/env python3
"""
Creates a conceptual workflow GIF showing the multi-agent bridge
"""
from PIL import Image, ImageDraw, ImageFont
import os
import logging

logger = logging.getLogger(__name__)


def create_text_image(
    text,
    width=1200,
    height=200,
    bg_color=(30, 30, 30),
    text_color=(255, 255, 255),
    font_size=40,
):
    """Create an image with centered text"""
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.tt", font_size)
    except Exception as e:
        try:
            font = ImageFont.truetype("arial.tt", font_size)
        except Exception as e2:
            logger.warning(
                f"Could not load TrueType fonts ({e}, {e2}), using default font"
            )
            font = ImageFont.load_default()

    # Get text bbox
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center the text
    x = (width - text_width) // 2
    y = (height - text_height) // 2

    draw.text((x, y), text, fill=text_color, font=font)
    return img


def create_workflow_diagram(width=1200, height=400):
    """Create a workflow diagram"""
    img = Image.new("RGB", (width, height), (30, 30, 30))
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.tt", 32)
        font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.tt", 24)
    except Exception as e:
        logger.warning(f"Could not load TrueType fonts ({e}), using default font")
        title_font = font = ImageFont.load_default()

    # Title
    draw.text(
        (width // 2 - 200, 30),
        "Multi-Agent Communication Flow",
        fill=(255, 255, 255),
        font=title_font,
    )

    # Boxes
    box_width = 200
    box_height = 80
    y_pos = 150

    # Code Claude box
    x1 = 100
    draw.rectangle(
        [(x1, y_pos), (x1 + box_width, y_pos + box_height)],
        outline=(100, 149, 237),
        width=3,
    )
    draw.text((x1 + 30, y_pos + 25), "Code Claude", fill=(100, 149, 237), font=font)

    # Arrow 1
    arrow_x = x1 + box_width + 20
    draw.line(
        [(x1 + box_width, y_pos + 40), (arrow_x + 80, y_pos + 40)],
        fill=(50, 205, 50),
        width=3,
    )
    draw.polygon(
        [
            (arrow_x + 80, y_pos + 40),
            (arrow_x + 65, y_pos + 35),
            (arrow_x + 65, y_pos + 45),
        ],
        fill=(50, 205, 50),
    )
    draw.text((arrow_x + 10, y_pos + 10), "Send", fill=(50, 205, 50), font=font)

    # Message Bus box
    x2 = arrow_x + 100
    draw.rectangle(
        [(x2, y_pos), (x2 + box_width, y_pos + box_height)],
        outline=(255, 215, 0),
        width=3,
    )
    draw.text((x2 + 20, y_pos + 25), "Message Bus", fill=(255, 215, 0), font=font)

    # Arrow 2
    arrow_x2 = x2 + box_width + 20
    draw.line(
        [(x2 + box_width, y_pos + 40), (arrow_x2 + 80, y_pos + 40)],
        fill=(50, 205, 50),
        width=3,
    )
    draw.polygon(
        [
            (arrow_x2 + 80, y_pos + 40),
            (arrow_x2 + 65, y_pos + 35),
            (arrow_x2 + 65, y_pos + 45),
        ],
        fill=(50, 205, 50),
    )
    draw.text((arrow_x2 + 10, y_pos + 10), "Route", fill=(50, 205, 50), font=font)

    # Browser Claude box
    x3 = arrow_x2 + 100
    draw.rectangle(
        [(x3, y_pos), (x3 + box_width, y_pos + box_height)],
        outline=(147, 112, 219),
        width=3,
    )
    draw.text((x3 + 10, y_pos + 25), "Browser Claude", fill=(147, 112, 219), font=font)

    # Return arrow
    draw.line(
        [(x3, y_pos + box_height + 20), (x1 + box_width, y_pos + box_height + 20)],
        fill=(255, 99, 71),
        width=3,
    )
    draw.polygon(
        [
            (x1 + box_width, y_pos + box_height + 20),
            (x1 + box_width + 15, y_pos + box_height + 15),
            (x1 + box_width + 15, y_pos + box_height + 25),
        ],
        fill=(255, 99, 71),
    )
    draw.text(
        (width // 2 - 50, y_pos + box_height + 30),
        "Response",
        fill=(255, 99, 71),
        font=font,
    )

    return img


def create_demo_gif():
    """Create a demo GIF showing the workflow"""
    frames = []

    # Frame 1: Title
    frames.append(
        create_text_image("Claude Multi-Agent Bridge", font_size=60, height=300)
    )

    # Frame 2: Problem
    frames.append(
        create_text_image(
            "Problem: Copy-paste between Claude instances", font_size=35, height=250
        )
    )

    # Frame 3: Solution
    frames.append(
        create_text_image(
            "Solution: Direct AI-to-AI Communication",
            font_size=35,
            bg_color=(0, 60, 0),
            height=250,
        )
    )

    # Frame 4: Code example
    code_img = Image.new("RGB", (1200, 400), (20, 20, 20))
    draw = ImageDraw.Draw(code_img)
    try:
        font = ImageFont.truetype("C:\\Windows\\Fonts\\consola.tt", 28)
    except Exception as e:
        logger.warning(f"Could not load consola.ttf ({e}), using default font")
        font = ImageFont.load_default()

    code = """c.send('browser', 'command', {
    'text': 'What is 2+2?'
})

response = c.poll()  # "4" """

    y = 80
    for line in code.split("\n"):
        if "send" in line or "poll" in line:
            color = (100, 200, 255)  # Highlight key lines
        elif "#" in line:
            color = (100, 255, 100)  # Comments
        else:
            color = (200, 200, 200)  # Normal
        draw.text((50, y), line, fill=color, font=font)
        y += 45

    frames.append(code_img)

    # Frame 5: Workflow diagram
    frames.append(create_workflow_diagram())

    # Frame 6: Result
    frames.append(
        create_text_image(
            "Result: 5 steps → 1 line", font_size=50, bg_color=(0, 60, 120), height=300
        )
    )

    # Frame 7: GitHub CTA
    frames.append(
        create_text_image(
            "github.com/yakub268/claude-multi-agent-bridge",
            font_size=35,
            bg_color=(70, 30, 100),
            height=250,
        )
    )

    # Save as GIF
    output_path = "demo_workflow.gi"
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=2500,  # 2.5 seconds per frame
        loop=0,
    )

    print(f"✅ Created {output_path}")
    print(f"   {len(frames)} frames")
    print(f"   {len(frames) * 2.5} seconds total")
    return output_path


if __name__ == "__main__":
    print("Creating workflow demonstration GIF...")
    output = create_demo_gif()
    print(f"\nGIF created: {output}")
    print("\nThis is a conceptual demo. For a real demo:")
    print("  1. Run: python record_demo.py")
    print("  2. Screen record it (Win+G for Game Bar)")
    print("  3. Convert to GIF with: https://gifski.app")
