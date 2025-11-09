import threading
import queue
import re
import time
import tkinter as tk
from tkinter import font as tkfont
import customtkinter as ctk
import speech_recognition as sr
import pyttsx3
import eng_to_ipa as ipa

# -----------------------------
# App Config
# -----------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MIN_W, MIN_H = 1000, 800
CONTENT_WORD_POS_GUESS = {
    # Rough heuristic lists; we’ll treat these as FUNCTION words (lowercase).
    "function": set("""
a an the and but or so for nor of at by from with without within into onto to up down over under on in out as is am are was were be been being do does did have has had will would should could can may might must than then there here this that these those not no yes if also very just only maybe perhaps really about across after again against all almost already although always among around because before below between both each either enough ever every few fewer first former further
""".split())
}

AUX_STARTERS = {
    "is","are","am","was","were",
    "do","does","did",
    "have","has","had",
    "can","could","will","would","shall","should","may","might","must"
}

# -----------------------------
# Helper functions
# -----------------------------
def split_into_sentences(text: str):
    # Preserve ending punctuation to help intonation; simple robust split
    pieces = re.split(r'([.?!])', text)
    sentences = []
    for i in range(0, len(pieces), 2):
        if i < len(pieces):
            core = pieces[i].strip()
            end = pieces[i+1] if i+1 < len(pieces) else ''
            s = (core + end).strip()
            if s:
                sentences.append(s)
    return sentences

def is_yes_no_question(sentence: str):
    s = sentence.strip()
    if s.endswith('?'):
        return True  # simplest case
    # If no explicit '?', infer from auxiliary-initial
    words = re.findall(r"[A-Za-z']+", s.lower())
    return bool(words and words[0] in AUX_STARTERS)

def rhythm_transform(sentence: str):
    """
    Convert content words to UPPERCASE (stress); function words remain lowercase.
    Very lightweight heuristic: if a word is in FUNCTION list -> lowercase,
    else uppercase (keeping apostrophes).
    """
    out_tokens = []
    for token in re.findall(r"[A-Za-z']+|[^A-Za-z'\s]+|\s+", sentence, flags=re.UNICODE):
        if re.fullmatch(r"[A-Za-z']+", token):
            wlow = token.lower()
            if wlow in CONTENT_WORD_POS_GUESS["function"]:
                out_tokens.append(wlow)  # function words lowered
            else:
                out_tokens.append(token.upper())
        else:
            out_tokens.append(token)
    return "".join(out_tokens)

def compute_confidence_from_google_show_all(show_all):
    """
    Google Web Speech (via SpeechRecognition) returns a dict when show_all=True.
    Confidence may be on the first alternative or absent.
    """
    try:
        if isinstance(show_all, dict):
            alts = show_all.get('alternative', [])
            # Find the best alt with confidence if present
            best_conf = None
            for alt in alts:
                if 'confidence' in alt:
                    best_conf = alt['confidence']
                    break
            # Fallback: 1.0 if only transcript exists (Google sometimes omits confidence)
            if best_conf is None and alts:
                best_conf = alts[0].get('confidence', None)
            return best_conf
    except Exception:
        pass
    return None

def mk_arrow_and_color(is_yn):
    # Return arrow and a color for it
    # Rising for Yes/No; falling otherwise
    return ("↗", "#5AC8FA") if is_yn else ("↘", "#FFCC00")

def confidence_to_color_and_value(conf):
    # Map to color & normalized 0..1 for CTkProgressBar
    if conf is None:
        return ("#808080", 0.0, "N/A")
    pct = conf * 100.0
    if pct < 65:
        color = "#FF3B30"  # red
    elif pct < 85:
        color = "#FFCC00"  # yellow
    else:
        color = "#34C759"  # green
    return (color, max(0.0, min(1.0, conf)), f"{pct:.1f}%")

def safe_ipa(text):
    try:
        return ipa.convert(text)
    except Exception:
        return "(IPA unavailable)"

# -----------------------------
# App Class
# -----------------------------
class PronunciationTrainerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("English Pronunciation Trainer")
        self.minsize(MIN_W, MIN_H)

        # 50/50 split
        self.grid_columnconfigure(0, weight=1, uniform="half")
        self.grid_columnconfigure(1, weight=1, uniform="half")
        self.grid_rowconfigure(0, weight=1)

        # State
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 2.5  # crucial per spec
        self.audio_data = None
        self.transcript = ""
        self.confidence = None
        self.recording_thread = None
        self.recording_queue = queue.Queue()

        # Left Panel (Controls + Transcript)
        self.left = ctk.CTkFrame(self)
        self.left.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.left.grid_rowconfigure(2, weight=1)  # transcript grows
        self.left.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(self.left, text="Controls & Transcription", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_lbl.grid(row=0, column=0, sticky="w", pady=(4, 12))

        btn_row = ctk.CTkFrame(self.left)
        btn_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        btn_row.grid_columnconfigure((0,1,2), weight=1)

        self.record_btn = ctk.CTkButton(btn_row, text="🎙 Start Recording", command=self.handle_start_record)
        self.record_btn.grid(row=0, column=0, padx=6, sticky="ew")

        self.play_btn = ctk.CTkButton(btn_row, text="🔊 Playback Recording", command=self.handle_playback, state="disabled")
        self.play_btn.grid(row=0, column=1, padx=6, sticky="ew")

        self.clear_btn = ctk.CTkButton(btn_row, text="🧹 Clear", command=self.clear_all)
        self.clear_btn.grid(row=0, column=2, padx=6, sticky="ew")

        # Transcript box
        self.transcript_box = ctk.CTkTextbox(self.left, wrap="word", height=200)
        self.transcript_box.grid(row=2, column=0, sticky="nsew")
        self.transcript_box.insert("1.0", "Transcript will appear here...\n")
        self.transcript_box.configure(state="disabled")

        # Status line
        self.status_lbl = ctk.CTkLabel(self.left, text="Ready.", anchor="w")
        self.status_lbl.grid(row=3, column=0, sticky="ew", pady=(8,0))

        # Right Panel (Analysis)
        self.right = ctk.CTkFrame(self)
        self.right.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.right.grid_rowconfigure(5, weight=1)  # rhythm/intonation box grows
        self.right.grid_columnconfigure(0, weight=1)

        self.analysis_lbl = ctk.CTkLabel(self.right, text="Analysis", font=ctk.CTkFont(size=18, weight="bold"))
        self.analysis_lbl.grid(row=0, column=0, sticky="w", pady=(4, 8))

        # Accuracy gauge
        gauge_frame = ctk.CTkFrame(self.right)
        gauge_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        gauge_frame.grid_columnconfigure(0, weight=1)
        g_row = 0
        ctk.CTkLabel(gauge_frame, text="Accuracy (Confidence)").grid(row=g_row, column=0, sticky="w")
        g_row += 1
        self.conf_bar = ctk.CTkProgressBar(gauge_frame)
        self.conf_bar.grid(row=g_row, column=0, sticky="ew", pady=(4, 4))
        self.conf_bar.set(0.0)
        g_row += 1
        self.conf_val_lbl = ctk.CTkLabel(gauge_frame, text="N/A")
        self.conf_val_lbl.grid(row=g_row, column=0, sticky="w")

        # IPA line
        ipa_frame = ctk.CTkFrame(self.right)
        ipa_frame.grid(row=2, column=0, sticky="ew", pady=(8, 8))
        ipa_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(ipa_frame, text="IPA Transcription").grid(row=0, column=0, sticky="w")
        self.ipa_val = ctk.CTkTextbox(ipa_frame, wrap="word", height=60)
        self.ipa_val.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.ipa_val.insert("1.0", "(IPA will appear here)")
        self.ipa_val.configure(state="disabled")

        # Rhythm & Intonation (tk.Text for rich tagging)
        r_frame = ctk.CTkFrame(self.right)
        r_frame.grid(row=5, column=0, sticky="nsew", pady=(8, 0))
        r_frame.grid_rowconfigure(1, weight=1)
        r_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(r_frame, text="Target Rhythm & Intonation").grid(row=0, column=0, sticky="w")

        # Native tk.Text with dark styling + tags
        self.rhythm_text = tk.Text(
            r_frame,
            wrap="word",
            bg="#1A1A1A",       # dark
            fg="#D9D9D9",       # light text
            insertbackground="#D9D9D9",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2A2A2A",
            highlightcolor="#2A2A2A",
        )
        self.rhythm_text.grid(row=1, column=0, sticky="nsew", pady=(6,0))

        # Fonts/tags
        base_font = tkfont.Font(family="Segoe UI", size=12)
        bold_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.rhythm_text.configure(font=base_font)
        self.rhythm_text.tag_configure("bold", font=bold_font)
        self.rhythm_text.tag_configure("arrow_rise", foreground="#5AC8FA", font=bold_font)   # cyan
        self.rhythm_text.tag_configure("arrow_fall", foreground="#FFCC00", font=bold_font)   # yellow
        self.rhythm_text.tag_configure("content", foreground="#FFFFFF")
        self.rhythm_text.tag_configure("function", foreground="#D0D0D0")

        # Polling queue for background thread results
        self.after(100, self._poll_recording_queue)

    # -------------------------
    # UI Actions
    # -------------------------
    def handle_start_record(self):
        if self.recording_thread and self.recording_thread.is_alive():
            return
        self.status_lbl.configure(text="Listening… (pause for 2.5s to stop)")
        self.record_btn.configure(state="disabled")
        self.play_btn.configure(state="disabled")
        self.recording_thread = threading.Thread(target=self._record_and_transcribe, daemon=True)
        self.recording_thread.start()

    def handle_playback(self):
        if not self.transcript:
            return
        self.status_lbl.configure(text="Playing back slowly…")
        self.play_btn.configure(state="disabled")
        self.update_idletasks()
        try:
            # IMPORTANT: Re-initialize pyttsx3 each time
            engine = pyttsx3.init()
            engine.setProperty('rate', 140)
            engine.say(self.transcript)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            self.status_lbl.configure(text=f"TTS error: {e}")
        else:
            self.status_lbl.configure(text="Playback complete.")
        finally:
            self.play_btn.configure(state="normal")

    def clear_all(self):
        self.transcript = ""
        self.confidence = None
        self.audio_data = None
        self._set_transcript_text("(cleared)")
        self._update_confidence(None)
        self._set_ipa_text("(cleared)")
        self._set_rhythm_text("(cleared)")
        self.status_lbl.configure(text="Cleared.")
        self.play_btn.configure(state="disabled")

    # -------------------------
    # Recording & ASR
    # -------------------------
    def _record_and_transcribe(self):
        try:
            rec = self.recognizer
            with sr.Microphone() as source:
                # Slight ambient calibration
                try:
                    rec.adjust_for_ambient_noise(source, duration=0.5)
                except Exception:
                    pass
                audio = rec.listen(source, phrase_time_limit=None)  # will stop on pause_threshold
            self.audio_data = audio

            try:
                # get both transcript and show_all for confidence
                show_all = rec.recognize_google(audio, language="en-US", show_all=True)
                # Best transcript
                transcript = ""
                if isinstance(show_all, dict) and show_all.get("alternative"):
                    transcript = show_all["alternative"][0].get("transcript", "").strip()
                if not transcript:
                    transcript = rec.recognize_google(audio, language="en-US").strip()

                confidence = compute_confidence_from_google_show_all(show_all)

                self.recording_queue.put(("ok", transcript, confidence))
            except sr.UnknownValueError:
                self.recording_queue.put(("err", "Speech not understood.", None))
            except sr.RequestError as e:
                self.recording_queue.put(("err", f"ASR request error: {e}", None))
        except Exception as e:
            self.recording_queue.put(("err", f"Mic/recording error: {e}", None))

    def _poll_recording_queue(self):
        try:
            while True:
                msg = self.recording_queue.get_nowait()
                kind = msg[0]
                if kind == "ok":
                    transcript, confidence = msg[1], msg[2]
                    self._on_transcription_ready(transcript, confidence)
                else:
                    errtxt = msg[1]
                    self.status_lbl.configure(text=errtxt)
                    self.record_btn.configure(state="normal")
                    self.play_btn.configure(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.after(100, self._poll_recording_queue)

    def _on_transcription_ready(self, transcript, confidence):
        self.transcript = transcript
        self.confidence = confidence

        self._set_transcript_text(transcript)
        self._update_confidence(confidence)
        self._set_ipa_text(safe_ipa(transcript))
        self._update_rhythm_and_intonation(transcript)

        self.status_lbl.configure(text="Transcription complete.")
        self.record_btn.configure(state="normal")
        self.play_btn.configure(state="normal" if transcript else "disabled")

    # -------------------------
    # UI Updates
    # -------------------------
    def _set_transcript_text(self, text):
        self.transcript_box.configure(state="normal")
        self.transcript_box.delete("1.0", "end")
        self.transcript_box.insert("1.0", text if text else "(empty)")
        self.transcript_box.configure(state="disabled")

    def _update_confidence(self, conf):
        color, value, label = confidence_to_color_and_value(conf)
        # Update bar value and color
        try:
            self.conf_bar.set(value)
            # CTkProgressBar accepts "progress_color"
            self.conf_bar.configure(progress_color=color)
        except Exception:
            pass
        self.conf_val_lbl.configure(text=f"{label}")

    def _set_ipa_text(self, text):
        self.ipa_val.configure(state="normal")
        self.ipa_val.delete("1.0", "end")
        self.ipa_val.insert("1.0", text)
        self.ipa_val.configure(state="disabled")

    def _set_rhythm_text(self, text):
        self.rhythm_text.configure(state="normal")
        self.rhythm_text.delete("1.0", "end")
        self.rhythm_text.insert("1.0", text)
        self.rhythm_text.configure(state="disabled")

    def _update_rhythm_and_intonation(self, transcript):
        self.rhythm_text.configure(state="normal")
        self.rhythm_text.delete("1.0", "end")

        if not transcript.strip():
            self.rhythm_text.insert("1.0", "(no speech)")
            self.rhythm_text.configure(state="disabled")
            return

        sentences = split_into_sentences(transcript)
        for idx, s in enumerate(sentences):
            stressed = rhythm_transform(s)
            yn = is_yes_no_question(s)
            arrow, arrow_color = mk_arrow_and_color(yn)

            # Insert stressed sentence with simple bold tagging on all CAPS tokens
            start_idx = self.rhythm_text.index("end-1c")

            # Tokenize to separate words and spaces/punct
            tokens = re.findall(r"[A-Za-z']+|[^A-Za-z'\s]+|\s+", stressed)
            for t in tokens:
                if re.fullmatch(r"[A-Za-z']+", t):
                    if t.isupper():
                        self.rhythm_text.insert("end", t, ("bold", "content"))
                    else:
                        # function words (lowercase)
                        self.rhythm_text.insert("end", t, ("function",))
                else:
                    self.rhythm_text.insert("end", t)

            # Add space if line doesn't end with punctuation
            end_char = s.strip()[-1:] if s.strip() else ""
            if end_char not in ".?!":
                self.rhythm_text.insert("end", "")

            # Add arrow with color
            tag = "arrow_rise" if yn else "arrow_fall"
            self.rhythm_text.insert("end", "  " + arrow, (tag,))

            # Newline between sentences
            if idx < len(sentences) - 1:
                self.rhythm_text.insert("end", "\n")

        self.rhythm_text.configure(state="disabled")


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    app = PronunciationTrainerApp()
    app.mainloop()
