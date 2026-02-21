#!/usr/bin/env python3
"""
Fully automated demo GIF creator using screenshots
"""
from code_client import CodeClient
import time
from PIL import Image, ImageDraw, ImageFont
import os

class DemoGifCreator:
    def __init__(self):
        self.client = CodeClient()
        self.screenshots = []
        self.output_dir = "demo_frames"
        os.makedirs(self.output_dir, exist_ok=True)

    def create_text_frame(self, text, width=800, height=100, bg_color=(30, 30, 30), text_color=(255, 255, 255)):
        """Create a text-only frame"""
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Try to use a nice font, fall back to default
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()

        # Center the text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        draw.text((x, y), text, fill=text_color, font=font)
        return img

    def create_demo(self):
        """Create the demo and capture frames"""
        print("Starting automated demo GIF creation...")

        # Frame 1: Title
        frame1 = self.create_text_frame("Claude Multi-Agent Bridge Demo", height=150)
        self.screenshots.append(frame1)

        # Frame 2: Sending prompt
        frame2 = self.create_text_frame("Sending: What is the capital of France?", height=150)
        self.screenshots.append(frame2)

        # Send the actual message
        print("Sending message to Browser Claude...")
        self.client.send('browser', 'command', {
            'action': 'run_prompt',
            'text': 'What is the capital of France? Reply with just the city name.'
        })

        # Frame 3: Waiting
        frame3 = self.create_text_frame("Waiting for Browser Claude...", height=150)
        self.screenshots.append(frame3)

        # Poll for response
        print("Waiting for response...")
        response_text = None
        for i in range(20):
            time.sleep(1)
            messages = self.client.poll()

            for msg in messages:
                if msg.get('type') == 'claude_response':
                    response_text = msg['payload']['response']
                    break

            if response_text:
                break

        if response_text:
            # Frame 4: Response received
            frame4 = self.create_text_frame(f"Response: {response_text}", height=150)
            self.screenshots.append(frame4)

            # Frame 5: Success
            frame5 = self.create_text_frame("✅ Communication Successful!", height=150, bg_color=(0, 100, 0))
            self.screenshots.append(frame5)
        else:
            frame4 = self.create_text_frame("⏰ Timeout - no response", height=150, bg_color=(100, 0, 0))
            self.screenshots.append(frame4)

        # Create GIF
        print("Creating GIF...")
        self.create_gif()

    def create_gif(self):
        """Compile screenshots into GIF"""
        if not self.screenshots:
            print("No screenshots to compile!")
            return

        output_path = "demo.gif"

        # Save as GIF
        self.screenshots[0].save(
            output_path,
            save_all=True,
            append_images=self.screenshots[1:],
            duration=2000,  # 2 seconds per frame
            loop=0
        )

        print(f"✅ GIF created: {output_path}")
        print(f"   {len(self.screenshots)} frames")
        print(f"   Total duration: {len(self.screenshots) * 2} seconds")

def main():
    print("="*70)
    print("🎬 AUTOMATED DEMO GIF CREATOR")
    print("="*70)
    print()
    print("Requirements:")
    print("  1. server.py running (python server.py)")
    print("  2. Fresh claude.ai tab open with extension")
    print()
    input("Press Enter when ready...")
    print()

    creator = DemoGifCreator()
    creator.create_demo()

    print()
    print("="*70)
    print("Done! Check demo.gif")
    print("="*70)

if __name__ == '__main__':
    main()
