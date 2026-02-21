# How to Record a Live Demo GIF

## Quick Method (5 minutes)

### Step 1: Setup
```bash
# Terminal 1: Start the server
cd C:\Users\yakub\.claude-shared\multi_claude_bus
python server.py

# Terminal 2: Keep ready for demo script
cd C:\Users\yakub\.claude-shared\multi_claude_bus
```

### Step 2: Arrange Windows
- **Left half**: Terminal (will run demo script)
- **Right half**: Browser with fresh claude.ai tab (extension loaded)

### Step 3: Start Recording
**Option A - Windows Game Bar (Built-in)**
1. Press `Win + G`
2. Click "Capture"
3. Click record button (or `Win + Alt + R`)

**Option B - ShareX (Free, better)**
1. Download from https://getsharex.com/
2. Capture → Screen recording
3. Select region (both terminal and browser)

**Option C - OBS Studio (Professional)**
1. Download from https://obsproject.com/
2. Add "Display Capture" source
3. Start recording

### Step 4: Run Demo
```bash
# In Terminal 2
python record_demo.py
```

This will:
- Show a countdown (3 seconds)
- Send: "What is 2+2?"
- Poll for response
- Display result: "4"
- Show success message

**Total demo time:** ~20 seconds

### Step 5: Stop Recording
- Game Bar: `Win + Alt + R`
- ShareX: Click stop button
- OBS: Click "Stop Recording"

### Step 6: Convert to GIF

**Option A - Online (Easy)**
1. Upload MP4 to https://cloudconvert.com/mp4-to-gif
2. Settings: Width 800px, FPS 10
3. Download

**Option B - Gifski (Best Quality)**
1. Download from https://gif.ski/
2. Drag MP4 file
3. Adjust FPS (10-15 works well)
4. Export

**Option C - FFmpeg (Command Line)**
```bash
ffmpeg -i recording.mp4 -vf "fps=10,scale=800:-1:flags=lanczos" -c:v gif demo.gif
```

### Step 7: Optimize (Optional)
```bash
# Install gifsicle
choco install gifsicle

# Optimize
gifsicle -O3 --colors 256 demo.gif -o demo_optimized.gif
```

---

## Advanced: Split-Screen with Annotations

If you want a polished demo with callouts:

### Using OBS Studio + StreamFX

1. **Setup Sources**
   - Terminal capture (left)
   - Browser capture (right)
   - Text overlay for title

2. **Add Transitions**
   - Fade in at start
   - Highlight when message sends
   - Zoom on response

3. **Record at 60 FPS**
   - Better for slow-motion effects
   - Smooth animations

4. **Edit in DaVinci Resolve (Free)**
   - Add arrows pointing to key moments
   - Text callouts: "Message sent", "Response received"
   - Speed up boring parts (polling)

5. **Export**
   - 800x600px
   - 10 FPS for GIF
   - Or keep as MP4 for Twitter/YouTube

---

## Target Specs for README

- **Dimensions**: 800-1000px wide (mobile-friendly)
- **Duration**: 15-30 seconds (attention span)
- **FPS**: 10-15 (smooth but small file size)
- **File Size**: < 5 MB (GitHub limit: 10MB, but faster loads better)
- **Format**: GIF for README, MP4 for social media

---

## Example Timeline

A good demo shows:

1. **0:00-0:02** - Title card: "Multi-Agent Bridge Demo"
2. **0:02-0:05** - Show both windows (terminal + browser)
3. **0:05-0:08** - Terminal sends message
4. **0:08-0:12** - Browser receives, types, responds
5. **0:12-0:15** - Response appears in terminal
6. **0:15-0:18** - Success message
7. **0:18-0:20** - Freeze frame with GitHub URL

---

## Quick Start

If you just want to get SOMETHING published fast:

```bash
# Use the conceptual GIF already created
cp demo_workflow.gif README_demo.gif

# Then when you have time, record a real one
python record_demo.py  # while screen recording
```

The workflow GIF is good enough for initial launch. Real screencast can come later.

---

## Tips for Viral Demos

✅ Show the problem first (manual copy-paste)
✅ Then show the solution (one line)
✅ Use realistic example (not "hello world")
✅ Keep it under 20 seconds
✅ Add your GitHub username/URL at the end
✅ Loop seamlessly (fade out → fade in)

❌ Don't include setup/installation
❌ Don't show errors or retries
❌ Don't use tiny fonts (mobile users can't read)
❌ Don't make it too long (people scroll fast)
