# Quick Demo Recording (15 minutes)

## Option A: Simple GIF (Fastest)

**Tool:** ScreenToGif (free, Windows)
- Download: https://www.screentogif.com/

**Recording (30 seconds):**
1. Split screen: Terminal left | Browser right
2. Terminal: Type and run:
   ```python
   from code_client import CodeClient
   c = CodeClient()
   c.send('browser', 'command', {
       'action': 'run_prompt',
       'text': 'What is 2+2?'
   })
   ```
3. Show browser: Prompt appears, Claude responds "4"
4. Terminal: Show response with `c.poll()`

**Export:** Save as GIF, upload to LinkedIn post as edit

---

## Option B: Even Faster (5 min)

**Just take screenshots:**

1. **Screenshot 1:** Terminal with the send command
2. **Screenshot 2:** Browser showing Claude responding
3. **Screenshot 3:** Terminal showing response received

**Combine into single image** (Paint, PowerPoint, whatever)
**Add arrows** between screenshots
**Upload to LinkedIn** as image carousel

---

## Option C: Use Loom (10 min)

**Tool:** https://loom.com (free)

1. Click Chrome extension
2. Select "Screen + Camera" (or just screen)
3. Record the same flow as Option A
4. Get shareable link
5. Add to LinkedIn post + README

---

## What to Show

**The "wow" moment:**
- Terminal sends message
- Browser receives it AUTOMATICALLY
- No clicking, no switching tabs
- Response comes back

**Keep it under 60 seconds.**

---

## Post-Recording

**Add to:**
- LinkedIn post (edit and add video/GIF)
- GitHub README (embed Loom or add GIF)
- Show HN comment (edit with "Demo: [link]")

**Impact:** 2-5x more engagement, better understanding
