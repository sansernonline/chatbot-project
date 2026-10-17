"""Thai voice-over for the demo: one mp3 per scene in scenes.js, made with edge-tts (Microsoft's free online voices).

Sends only the narration text (`say`) to Microsoft. A scene whose text has not changed keeps its old mp3, so reruns send nothing new.
Writes _to_delete/e2e-demo-audio/manifest.json → {id: {file, seconds}}; demo.spec.js makes each scene as long as its voice,
finish.js lays the voices onto the video.

Run: python demo/tts.py      (npm run demo runs it first)   ·   DEMO_VOICE=th-TH-PremwadeeNeural for the female voice
"""
import asyncio
import hashlib
import json
import os
import subprocess
from pathlib import Path

import edge_tts

HERE = Path(__file__).parent
OUT = HERE.parents[2] / "_to_delete" / "e2e-demo-audio"
VOICE = os.environ.get("DEMO_VOICE", "th-TH-NiwatNeural")
RATE = os.environ.get("DEMO_RATE", "-8%")


def scenes():
    out = subprocess.run(["node", "-e", "console.log(JSON.stringify(require('./scenes')))"],
                         cwd=HERE, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return json.loads(out)


def seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return round(float(out.strip()), 2)


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for s in scenes():
        key = hashlib.sha1(f"{VOICE}|{RATE}|{s['say']}".encode()).hexdigest()[:10]
        mp3 = OUT / f"{s['id']}-{key}.mp3"
        if not mp3.exists():
            await edge_tts.Communicate(s["say"], VOICE, rate=RATE).save(str(mp3))
            print(f"สร้างเสียง {s['id']}")
        manifest[s["id"]] = {"file": str(mp3), "seconds": seconds(mp3)}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"เสียงพากย์ {len(manifest)} ข้อ รวม {sum(m['seconds'] for m in manifest.values()):.0f} วินาที · {VOICE}")


asyncio.run(main())
