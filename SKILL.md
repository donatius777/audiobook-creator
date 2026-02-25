---
name: audiobook-creator
description: Convert PDF books and documents into streaming audiobooks with a web-based chapter player. Uses edge-tts for text-to-speech, pdfplumber for text extraction, and a Node.js streaming server for playback and download. Use when the user asks to convert a PDF to audio, create an audiobook from a PDF, make a PDF listenable, or turn a document into speech. Triggers include audiobook, text to speech, PDF to audio, read PDF aloud, TTS, listen to book, convert book to audio, audiobook creator.
---

# Audiobook Creator

Convert PDF documents into chapter-based audiobooks with a web streaming player.

## Dependencies

Install before running:
```bash
pip install pdfplumber edge-tts --break-system-packages -q
sudo apt-get install -y -qq ffmpeg
```

## Workflow

### Step 1: Extract Text

Run `scripts/extract_text.py` to extract all text:

```bash
python3 <skill_path>/scripts/extract_text.py <input.pdf> tmp/full_text.txt
```

### Step 2: Identify Chapters and Clean Text

Read the extracted text to identify chapter boundaries. Search for patterns like `^Chapter \d`, `^Chapter (One|Two|...)`, section headers, or TOC entries.

Write a Python script in `tmp/` that:
1. Reads `tmp/full_text.txt`
2. Removes page markers (`===PAGE N===`), standalone page numbers, running headers
3. Splits text at chapter boundaries into separate files
4. Cleans each chapter for TTS: replaces `&` with `and`, joins wrapped lines into paragraphs, collapses whitespace
5. Writes numbered files to `tmp/chapters/` (e.g., `00_front_matter.txt`, `01_introduction.txt`, `02_ch01_title.txt`)

Key cleaning for TTS:
- Remove page markers: `re.sub(r"={10,}\nPAGE \d+\n={10,}\n?", "\n", text)`
- Remove standalone page numbers: `re.sub(r"\n\d{1,3}\n", "\n", text)`
- Join paragraph lines: split on `\n\n`, then `p.replace("\n", " ").strip()` within each
- Remove running headers (book/chapter title repeated at page tops)

### Step 3: Generate Audio

Run `scripts/generate_tts.py`:

```bash
python3 <skill_path>/scripts/generate_tts.py tmp/chapters/ tmp/audio/ [voice] [rate]
```

Default: `en-US-GuyNeural` at `-5%` rate. Other voices: `en-US-JennyNeural` (female), `en-GB-RyanNeural` (British), `en-US-AriaNeural` (female, clear).

The script automatically chunks chapters exceeding 20K characters, retries failures, and splits further if needed.

### Step 4: Launch Streaming Player

Copy assets and configure:

```bash
mkdir -p tmp/audiobook_server
cp <skill_path>/assets/player_server.js tmp/audiobook_server/server.js
cp <skill_path>/assets/player.html tmp/audiobook_server/player.html
```

Create `tmp/audio/chapters.json`:

```python
import json, glob, os
chapters = []
for f in sorted(glob.glob("tmp/audio/[0-9]*.mp3")):
    chapters.append({"file": os.path.basename(f), "title": "descriptive title here"})
with open("tmp/audio/chapters.json", "w") as fp:
    json.dump(chapters, fp)
```

Start server and export port:

```bash
AUDIO_DIR=tmp/audio TITLE="Book Title" AUTHOR="Author Name" \
  HTML_FILE=tmp/audiobook_server/player.html \
  nohup node tmp/audiobook_server/server.js &>/tmp/audiobook_server.log &
sleep 2
/app/export-port.sh 8080
```

The player provides: chapter playback with auto-advance, play/pause/skip, progress seek, speed control (0.75x-2x), and full audiobook download via `/download-all`.

## Critical Notes

- **Never use file attachments for audio.** Binary file downloads are corrupted on this platform. Always use the streaming server.
- **ffmpeg may vanish between commands.** Use `/usr/bin/ffmpeg` or reinstall with `sudo apt-get install -y -qq ffmpeg`.
- **edge-tts limit is ~25K chars per request.** The TTS script handles this via chunking.
- **Download button must use `window.open('/download-all', '_blank')`**, not `<a download>`, because the download attribute fails in cross-origin iframes.
