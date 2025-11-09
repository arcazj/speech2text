# English Pronunciation Trainer — README.md

[![UI](https://img.shields.io/badge/UI-dark%20%2B%20blue-3b82f6)](#) [![Speech](https://img.shields.io/badge/Speech-STT%20%2F%20TTS-success)](#) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🚀 Live Demo

**▶️ [Open the LIVE DEMO](https://arcazj.github.io/speech2text/index.html)**


---

## Overview

A modern English pronunciation trainer featuring:

* **50/50 split layout** (left: controls/transcription; right: analysis)
* **Dark / blue theme**
* **Speech-to-Text**

  * Web: **Web Speech API** (Chrome/Edge)
  * Python: **SpeechRecognition** → Google Web Speech
* **Slow playback**

  * Web: `speechSynthesis`
  * Python: `pyttsx3` (engine **re-initialized on every click**)
* **IPA**

  * Web: lightweight inline helper
  * Python: `eng_to_ipa`
* **Target Rhythm & Intonation:** content words in **UPPERCASE + bold**, function words lowercase, arrows:

  * **↗** Yes/No questions
  * **↘** Other sentences
* **Accuracy Gauge** with thresholds: **Red** < 65% • **Yellow** < 85% • **Green** ≥ 85%

---

## Project Tools

This project provides **three tools**:

| File                                 | Type                | Summary                                                                                                                                                                                                       |
| ------------------------------------ | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `speech2text_chatGPT.py`             | Python desktop GUI  | `customtkinter` app (dark/blue). Threaded mic capture with `pause_threshold=2.5`, Google Web Speech transcript **+ confidence**, IPA via `eng_to_ipa`, slow playback with `pyttsx3` (fresh engine each time). |
| `speech2text_gemini2.5.py`           | Python template     | Alternative STT/analysis pipeline wired for Gemini 2.5 (add your API calls/keys).                                                                                                                             |
| `speech2text_chatGPT_web_based.html` | Single-file web app | All-in-one HTML+JS using Web Speech API, `speechSynthesis`, rhythm/intonation rendering, and confidence gauge. Best on Chrome/Edge.                                                                           |

---

## Quick Start

### A) Single-File Web App

1. Open `speech2text_chatGPT_web_based.html` in **Chrome** or **Edge**.
2. Click **Start Recording**, speak, then **pause ~2.5s** to auto-stop.
3. Review **Transcript**, **Confidence**, **IPA**, and **Rhythm & Intonation**.
4. Click **Playback Recording** for slow TTS.

**Browser support:** Chrome/Edge ✅ • Safari ⚠️ partial • Firefox ❌ (no Web Speech STT)

---

### B) Python GUI (customtkinter)

**Requirements**

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install customtkinter SpeechRecognition pyttsx3 eng_to_ipa pyaudio
# If PyAudio fails on Windows:
#   pip install pipwin && pipwin install pyaudio
```

**Run**

```bash
python speech2text_chatGPT.py
```

**Notes**

* `recognizer.pause_threshold = 2.5` (auto-stop after ~2.5s silence)
* Confidence sometimes omitted by Google Web Speech → gauge shows **N/A**
* `pyttsx3` engine is **re-initialized** per playback to avoid event-loop hangs

---

### C) Gemini 2.5 Variant (Python)

Use `speech2text_gemini2.5.py` as a **template** to call Gemini 2.5 for STT/analysis.
Add credentials (env vars/config) and plug in your API calls.

---

## How It Works

* **Sentence Split:** punctuation-aware (`. ? !`)
* **Rhythm:** function words (articles, prepositions, auxiliaries, pronouns) remain lowercase; content words → **UPPERCASE + bold**
* **Intonation:**

  * Yes/No question (leading auxiliary or `?`) → **↗**
  * Otherwise → **↘**
* **Confidence Gauge:**

  * **Red** < 65% • **Yellow** < 85% • **Green** ≥ 85%

---

## Deploying the Live Demo (GitHub Pages)

1. Commit `speech2text_chatGPT_web_based.html` to repo root.
2. **Settings → Pages** → Build and deployment:

   * Source: **Deploy from a branch**
   * Branch: **main** (or default) and **/root**
3. After deployment, update the Live Demo link to:
   `https://YOUR_USERNAME.github.io/YOUR_REPO/speech2text_chatGPT_web_based.html`

---

## 🧠 AI Generation Prompts

To reproduce the core implementations, these are the prompts used:

### 1) Python GUI (customtkinter)

```
Create a modern, professional Python GUI application for English pronunciation training. Use customtkinter for the interface (dark mode, blue theme) and SpeechRecognition, pyttsx3, and eng_to_ipa for functionality.

Core Requirements:

Layout: A 50/50 split window (min 1000x800). Left side for controls/transcription, right side for analysis.

Audio Input: A "Start Recording" button that listens indefinitely until the user pauses for 2.5 seconds (use recognizer.pause_threshold = 2.5). Use threading so the GUI doesn't freeze.

Transcription: Use Google Web Speech API to get both the transcript and a confidence score (0.0-1.0).

Playback: A "Playback Recording" button that uses pyttsx3 to read the transcript back slowly (rate ~140). Important: Re-initialize the TTS engine on every button press to prevent event loop hangs.

Analysis Features (Right Panel):

Accuracy Gauge: A progress bar showing the confidence score, changing color (Red < 65%, Yellow < 85%, Green > 85%).

Phonetics: Display the IPA transcription of the user's speech.

Target Rhythm & Intonation (Crucial): A text box showing how the user should have said the phrase.

Logic: Split the transcript into sentences.

Rhythm: Convert "content words" (nouns, verbs, etc.) to UPPERCASE (stress) and keep "function words" (the, a, is, to) lowercase.

Intonation: Append a rising arrow (↗) if it's a Yes/No question, or a falling arrow (↘) for other sentences, at the end of every line.

Tech Note: Use standard tk.Text widgets for this box (with dark styling manually applied) because customtkinter textboxes do not support the specific rich text tagging needed for colored arrows and bold text.
```

### 2) Single-File Web Version

```
Build a self-contained HTML file that recreates the features entirely in the browser:

- Use Web Speech API (webkitSpeechRecognition) for recording/transcription with continuous recognition.
- Implement a 2.5s inactivity watchdog to stop listening (browsers lack pause_threshold).
- Use speechSynthesis for slow playback (fresh SpeechSynthesisUtterance each time).
- Replicate the 50/50 dark UI, accuracy gauge (color thresholds), sentence splitting, rhythm transform (content words UPPERCASE/bold, function words lowercase), and intonation arrows (↗ Yes/No, ↘ otherwise).
- Provide a simple IPA helper (small inline dictionary + naive fallback) since eng_to_ipa is Python-only.
- No external libraries or servers; a single HTML file that works in Chrome/Edge.
```

---

## Privacy & Keys

* **Web demo** uses the browser’s **Web Speech API**; typically no API key needed (Chrome/Edge). Audio may be sent to provider servers per browser policies.
* **Python** demo uses `SpeechRecognition` → **Google Web Speech** (no Google Cloud key).
  For enterprise, consider **Google Cloud STT**, OpenAI Realtime/STT, or **Vosk** (offline). Store keys in env vars, not code.

---

## Roadmap

* Larger IPA dictionary / client-side G2P (WASM)
* Offline STT in browser (e.g., Vosk WASM)
* Export session results (CSV/JSON)
* Target phrase packs + scoring rubric

---

## License

MIT © arcazj
See [`LICENSE`](LICENSE) for details.

---

## Acknowledgments

* Python: `customtkinter`, `SpeechRecognition`, `pyttsx3`, `eng_to_ipa`
* Web: Web Speech API, `speechSynthesis`
