import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import speech_recognition as sr
import pyttsx3
import eng_to_ipa as ipa
import threading
import re

# --- Configuration & Constants ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

FUNCTION_WORDS = {
    "a", "an", "the", "and", "but", "or", "for", "nor", "so", "yet",
    "at", "by", "for", "from", "in", "into", "of", "off", "on", "onto",
    "over", "out", "up", "with", "to", "as", "is", "am", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "can", "could", "will", "would", "shall", "should", "may",
    "might", "must", "i", "you", "he", "she", "it", "we", "they", "me",
    "him", "her", "us", "them", "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those"
}

YES_NO_STARTERS = {
    "am", "is", "are", "was", "were", "have", "has", "had", "do", "does",
    "did", "can", "could", "will", "would", "shall", "should", "may", "might", "must"
}

class PronunciationTrainer(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Main Window Setup ---
        self.title("Modern English Pronunciation Trainer")
        self.geometry("1100x850")
        self.minsize(1000, 800)

        # Grid layout: 1 row, 2 columns (50/50 split)
        self.grid_columnconfigure(0, weight=1, uniform="split")
        self.grid_columnconfigure(1, weight=1, uniform="split")
        self.grid_rowconfigure(0, weight=1)

        # State variables
        self.is_recording = False
        self.current_transcript = ""

        # --- Init UI Components ---
        self._setup_left_panel()
        self._setup_right_panel()

    def _setup_left_panel(self):
        self.left_frame = ctk.CTkFrame(self, corner_radius=0)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
        self.left_frame.grid_rowconfigure(4, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # 1. Header
        self.lbl_header_l = ctk.CTkLabel(self.left_frame, text="Input & Controls", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_header_l.grid(row=0, column=0, padx=20, pady=(30, 20), sticky="w")

        # 2. Status Indicator
        self.status_var = ctk.StringVar(value="Ready")
        self.lbl_status = ctk.CTkLabel(self.left_frame, textvariable=self.status_var, font=ctk.CTkFont(size=16), text_color="gray")
        self.lbl_status.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # 3. Control Buttons
        self.btn_record = ctk.CTkButton(self.left_frame, text="Start Recording", command=self.toggle_recording, height=50, font=ctk.CTkFont(size=18))
        self.btn_record.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.btn_playback = ctk.CTkButton(self.left_frame, text="Playback Recording", command=self.play_tts, height=50, font=ctk.CTkFont(size=18), fg_color="transparent", border_width=2, state="disabled")
        self.btn_playback.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # 4. Transcript Box
        self.lbl_trans = ctk.CTkLabel(self.left_frame, text="Transcript:", anchor="w")
        self.lbl_trans.grid(row=4, column=0, padx=20, pady=(20, 0), sticky="nw")

        self.txt_transcript = ctk.CTkTextbox(self.left_frame, font=ctk.CTkFont(size=16), wrap="word")
        self.txt_transcript.grid(row=5, column=0, padx=20, pady=(5, 30), sticky="nsew")

    def _setup_right_panel(self):
        self.right_frame = ctk.CTkFrame(self, corner_radius=0)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=0)
        self.right_frame.grid_columnconfigure(0, weight=1)

        # 1. Header
        self.lbl_header_r = ctk.CTkLabel(self.right_frame, text="Analysis", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_header_r.grid(row=0, column=0, padx=20, pady=(30, 20), sticky="w")

        # 2. Accuracy Gauge
        self.lbl_acc_title = ctk.CTkLabel(self.right_frame, text="Confidence Score:", anchor="w")
        self.lbl_acc_title.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")

        self.acc_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.acc_frame.grid(row=2, column=0, padx=20, pady=(5, 20), sticky="ew")

        self.progress_acc = ctk.CTkProgressBar(self.acc_frame, height=20)
        self.progress_acc.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.progress_acc.set(0)

        self.lbl_acc_val = ctk.CTkLabel(self.acc_frame, text="0%", width=50)
        self.lbl_acc_val.pack(side="right")

        # 3. Phonetics (IPA)
        self.lbl_ipa_title = ctk.CTkLabel(self.right_frame, text="Phonetics (IPA):", anchor="w")
        self.lbl_ipa_title.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")

        self.txt_ipa = ctk.CTkTextbox(self.right_frame, height=100, font=ctk.CTkFont(family="Segoe UI Historic", size=16), wrap="word")
        self.txt_ipa.grid(row=4, column=0, padx=20, pady=(5, 20), sticky="ew")

        # 4. Rhythm & Intonation (Target)
        self.lbl_rhythm_title = ctk.CTkLabel(self.right_frame, text="Target Rhythm & Intonation:", anchor="w")
        self.lbl_rhythm_title.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")

        # Tech Note: Using standard tk.Text for rich text tagging (bolding/coloring arrows)
        # We wrap it in a CTkFrame to maintain the border look
        self.rhythm_container = ctk.CTkFrame(self.right_frame)
        self.rhythm_container.grid(row=6, column=0, padx=20, pady=(5, 30), sticky="nsew")
        self.right_frame.grid_rowconfigure(6, weight=1) # Let this one expand

        self.txt_rhythm = tk.Text(self.rhythm_container, bg="#2B2B2B", fg="#DCE4EE",
                                  font=("Arial", 16), wrap="word", relief="flat", highlightthickness=0)
        self.txt_rhythm.pack(fill="both", expand=True, padx=5, pady=5)

        # Define tags for rich text
        self.txt_rhythm.tag_configure("stress", font=("Arial", 16, "bold"), foreground="#FFFFFF")
        self.txt_rhythm.tag_configure("unstress", font=("Arial", 14), foreground="#A0A0A0")
        self.txt_rhythm.tag_configure("rising", foreground="#4CC2FF", font=("Arial", 20))
        self.txt_rhythm.tag_configure("falling", foreground="#FF9900", font=("Arial", 20))

    # --- Core Logic ---

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.btn_record.configure(text="Listening... (Stop by pausing)", fg_color="#990000", hover_color="#660000")
            self.status_var.set("Listening (Wait 2.5s after speaking)...")
            self.btn_playback.configure(state="disabled")
            # Clear previous data
            self.txt_transcript.delete("0.0", "end")
            self.txt_ipa.delete("0.0", "end")
            self.txt_rhythm.delete("1.0", tk.END)
            self.progress_acc.set(0)
            self.lbl_acc_val.configure(text="0%")

            # Start thread
            threading.Thread(target=self._record_thread, daemon=True).start()
        else:
            # Manual stop if needed, though pause_threshold handles it mostly
            self.is_recording = False
            self.status_var.set("Stopping...")

    def _record_thread(self):
        r = sr.Recognizer()
        # Crucial requirement: 2.5 second pause threshold
        r.pause_threshold = 2.5
        r.energy_threshold = 300 # mildly adjust for background noise
        r.dynamic_energy_threshold = True

        try:
            with sr.Microphone() as source:
                # Short ambient noise adjustment before listening
                r.adjust_for_ambient_noise(source, duration=1)
                audio = r.listen(source, timeout=None) # Listen indefinitely until pause

            self.status_var.set("Processing speech...")
            # Use show_all=True to get raw JSON with confidence alternatives
            response = r.recognize_google(audio, show_all=True)

            # Schedule UI update on main thread
            self.after(0, lambda: self._process_results(response))

        except sr.WaitTimeoutError:
            self.after(0, lambda: self._handle_error("Listening timed out. No speech detected."))
        except sr.RequestError as e:
            self.after(0, lambda: self._handle_error(f"API Error: {e}"))
        except sr.UnknownValueError:
            self.after(0, lambda: self._handle_error("Could not understand audio."))
        except Exception as e:
            self.after(0, lambda: self._handle_error(f"Error: {e}"))

    def _handle_error(self, msg):
        self.status_var.set(msg)
        self.reset_record_button()

    def reset_record_button(self):
        self.is_recording = False
        self.btn_record.configure(text="Start Recording", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"], hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"])

    def _process_results(self, response):
        self.reset_record_button()
        self.status_var.set("Analysis Complete")
        self.btn_playback.configure(state="normal")

        transcript = ""
        confidence = 0.0

        # Parse Google's 'show_all' JSON response
        if isinstance(response, dict) and 'alternative' in response:
            # Best result is usually first
            best = response['alternative'][0]
            transcript = best.get('transcript', "")
            confidence = best.get('confidence', 0.0)
        elif isinstance(response, list) and len(response) > 0:
            # Sometimes it returns a list directly depending on library version quirks
            pass

            # Update Transcript
        self.current_transcript = transcript
        self.txt_transcript.insert("0.0", transcript)

        # Update Confidence Gauge
        self._update_confidence(confidence)

        # Update IPA
        ipa_text = ipa.convert(transcript)
        self.txt_ipa.insert("0.0", ipa_text)

        # Update Rhythm/Intonation
        self._analyze_rhythm_intonation(transcript)

    def _update_confidence(self, score):
        # Score is 0.0 to 1.0
        self.progress_acc.set(score)
        self.lbl_acc_val.configure(text=f"{int(score * 100)}%")

        # Color coding
        if score < 0.65:
            col = "#D32F2F" # Red
        elif score < 0.85:
            col = "#FBC02D" # Yellow/Orange
        else:
            col = "#388E3C" # Green
        self.progress_acc.configure(progress_color=col)

    def _analyze_rhythm_intonation(self, text):
        self.txt_rhythm.delete("1.0", tk.END)

        # Simple sentence splitter (handles ., ?, !)
        sentences = re.split(r'(?<=[.?!])\s+', text)

        for sentence in sentences:
            if not sentence.strip(): continue

            # 1. Determine Intonation (based on last char or starting word)
            clean_sent = sentence.strip().lower()
            # Check if it's a question
            is_question = clean_sent.endswith("?")
            # Check if it's specifically a YES/NO question (starts with auxiliary verb)
            first_word = clean_sent.split(' ')[0] if ' ' in clean_sent else clean_sent.strip('.?!')
            is_yes_no = is_question and (first_word in YES_NO_STARTERS)

            intonation_arrow = " ↗\n" if is_yes_no else " ↘\n"
            arrow_tag = "rising" if is_yes_no else "falling"

            # 2. Process Rhythm (word by word)
            # Remove punctuation for word checking, but keep for display if possible.
            # For simplicity, we'll just split by space and re-attach basic punctuation.
            words = sentence.split()
            for word in words:
                # Strip punctuation to check against function word list
                clean_word = re.sub(r'[^\w\s]', '', word).lower()

                if clean_word in FUNCTION_WORDS:
                    # Function word -> lowercase, unstressed
                    self.txt_rhythm.insert(tk.END, word.lower() + " ", "unstress")
                else:
                    # Content word -> UPPERCASE, stressed
                    self.txt_rhythm.insert(tk.END, word.upper() + " ", "stress")

            # Append intonation arrow at the end of the line
            self.txt_rhythm.insert(tk.END, intonation_arrow, arrow_tag)

    def play_tts(self):
        if not self.current_transcript: return

        # Disable button during playback to prevent spamming
        self.btn_playback.configure(state="disabled", text="Playing...")

        # Thread audio playback so GUI doesn't freeze
        threading.Thread(target=self._tts_thread, daemon=True).start()

    def _tts_thread(self):
        try:
            # Crucial: Initialize a NEW engine instance every time for robustness against hangs
            engine = pyttsx3.init()
            engine.setProperty('rate', 140) # Slower rate for clarity
            engine.say(self.current_transcript)
            engine.runAndWait()
            engine.stop()
            # Clean up explicitly if possible, though Python GC usually handles it.
            del engine
        except Exception as e:
            print(f"TTS Error: {e}")
        finally:
            # Restore button on main thread
            self.after(0, lambda: self.btn_playback.configure(state="normal", text="Playback Recording"))

if __name__ == "__main__":
    try:
        app = PronunciationTrainer()
        app.mainloop()
    except Exception as e:
        print(f"Failed to start: {e}")