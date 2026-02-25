#!/usr/bin/env python3
"""
Generate TTS audio from chapter text files using edge-tts.
Handles large chapters by chunking. Produces per-chapter MP3 files.

Usage: python3 generate_tts.py <chapters_dir> <audio_output_dir> [--voice VOICE] [--rate RATE]
"""
import asyncio
import os
import sys
import glob
import subprocess
import time

MAX_CHUNK_CHARS = 20000

def split_text_into_chunks(text, max_chars=MAX_CHUNK_CHARS):
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk = (current_chunk + "\n\n" + para) if current_chunk else para
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


async def generate_chunk_audio(text, output_file, voice, rate, retries=3):
    import edge_tts
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(output_file)
            return True
        except Exception as e:
            if attempt < retries - 1:
                print(f"    Retry {attempt + 1}/{retries}: {e}")
                await asyncio.sleep(2)
            else:
                # Try splitting in half
                if len(text) > 5000:
                    mid = len(text) // 2
                    bp = text.rfind("\n\n", 0, mid + 1000)
                    if bp == -1:
                        bp = text.rfind(". ", 0, mid + 500) + 1
                    if bp <= 0:
                        bp = mid
                    out1 = output_file.replace(".mp3", "_a.mp3")
                    out2 = output_file.replace(".mp3", "_b.mp3")
                    ok1 = await generate_chunk_audio(text[:bp].strip(), out1, voice, rate, retries)
                    ok2 = await generate_chunk_audio(text[bp:].strip(), out2, voice, rate, retries)
                    if ok1 and ok2:
                        cl = output_file.replace(".mp3", "_list.txt")
                        with open(cl, "w") as f:
                            f.write(f"file '{out1}'\nfile '{out2}'\n")
                        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                                        "-i", cl, "-c", "copy", output_file],
                                       capture_output=True)
                        for tmp in [out1, out2, cl]:
                            if os.path.exists(tmp):
                                os.remove(tmp)
                        return True
                print(f"    FAILED: {e}")
                return False
    return False


async def generate_chapter(chapter_file, output_file, voice, rate):
    with open(chapter_file, "r") as f:
        text = f.read().strip()
    if not text:
        return False

    chunks = split_text_into_chunks(text)
    basename = os.path.basename(chapter_file)

    if len(chunks) == 1:
        print(f"  {basename} ({len(text)} chars, 1 chunk)...")
        return await generate_chunk_audio(text, output_file, voice, rate)

    print(f"  {basename} ({len(text)} chars, {len(chunks)} chunks)...")
    chunk_files = []
    for i, chunk in enumerate(chunks):
        cf = output_file.replace(".mp3", f"_chunk{i:03d}.mp3")
        print(f"    Chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
        if await generate_chunk_audio(chunk, cf, voice, rate):
            chunk_files.append(cf)
        await asyncio.sleep(0.5)

    if not chunk_files:
        return False

    cl = output_file.replace(".mp3", "_chunks.txt")
    with open(cl, "w") as f:
        for cf in chunk_files:
            f.write(f"file '{cf}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", cl, "-c", "copy", output_file], capture_output=True)
    for cf in chunk_files:
        os.remove(cf)
    os.remove(cl)
    return os.path.exists(output_file) and os.path.getsize(output_file) > 100


async def main():
    chapters_dir = sys.argv[1]
    audio_dir = sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else "en-US-GuyNeural"
    rate = sys.argv[4] if len(sys.argv) > 4 else "-5%"

    try:
        import edge_tts
    except ImportError:
        os.system("pip install edge-tts --break-system-packages -q")

    os.makedirs(audio_dir, exist_ok=True)

    chapter_files = sorted(glob.glob(os.path.join(chapters_dir, "[0-9]*.txt")))
    chapter_files = [f for f in chapter_files if "manifest" not in f]
    print(f"Found {len(chapter_files)} chapters | Voice: {voice} | Rate: {rate}")

    start = time.time()
    audio_files = []

    for cf in chapter_files:
        basename = os.path.splitext(os.path.basename(cf))[0]
        out = os.path.join(audio_dir, f"{basename}.mp3")
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            print(f"  Skipping (exists): {basename}.mp3")
            audio_files.append(out)
            continue
        if await generate_chapter(cf, out, voice, rate):
            audio_files.append(out)
            sz = os.path.getsize(out) / 1024 / 1024
            print(f"    -> {sz:.1f} MB")
        else:
            print(f"  FAILED: {basename}")

    print(f"\nGenerated {len(audio_files)} audio files in {time.time()-start:.0f}s")

    # Write manifest
    manifest = os.path.join(audio_dir, "manifest.txt")
    with open(manifest, "w") as f:
        for af in audio_files:
            f.write(af + "\n")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generate_tts.py <chapters_dir> <audio_dir> [voice] [rate]")
        sys.exit(1)
    asyncio.run(main())
