#!/usr/bin/env python3
"""
Creates a demo GIF showing the multi-agent bridge in action
"""
import time
import subprocess
import sys
from pathlib import Path

def create_gif():
    """Create demo GIF by recording the demo script"""
    print("="*70)
    print("🎬 CREATING DEMO GIF")
    print("="*70)
    print()

    # Instructions
    print("This will create a demo GIF showing:")
    print("  1. Code sending a prompt")
    print("  2. Browser Claude receiving it")
    print("  3. Response coming back")
    print()
    print("SETUP REQUIRED:")
    print("  1. Make sure server.py is running (python server.py)")
    print("  2. Have a fresh claude.ai tab open with extension loaded")
    print("  3. Position windows side-by-side:")
    print("     - Left: Terminal running this script")
    print("     - Right: Browser with claude.ai")
    print()

    input("Press Enter when ready...")
    print()

    print("Starting demo in 3 seconds...")
    print("(Screen recording will capture next 30 seconds)")
    time.sleep(3)

    # Run the demo script
    print("\n" + "="*70)
    print("Running demo script...")
    print("="*70 + "\n")

    subprocess.run([sys.executable, "demo_script.py"])

    print()
    print("="*70)
    print("Demo complete!")
    print("="*70)
    print()
    print("TO CREATE GIF:")
    print("  1. Use OBS Studio / ShareX / Windows Game Bar to record")
    print("  2. Convert to GIF using: https://gifski.app or ffmpeg")
    print("  3. Or use: ffmpeg -i recording.mp4 -vf 'fps=10,scale=800:-1' demo.gi")
    print()
    print("ALTERNATIVE - Quick screenshot method:")
    print("  Use Windows Snipping Tool in video mode (Win+Shift+S)")
    print()

if __name__ == '__main__':
    create_gif()
