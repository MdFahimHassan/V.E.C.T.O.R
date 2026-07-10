# 🤖 V.E.C.T.O.R.

**Voice Executed Computer Task & Operations Router**

V.E.C.T.O.R. is a lightweight, hands-free Python desktop assistant designed to bridge the gap between spoken language and local operating system automation. Inspired by classic sci-fi virtual assistants, this project focuses on modular systems integration—allowing you to control applications, execute system macros, and navigate your workspace entirely via voice commands.

The project is architected defensively, ensuring that the core input/output pipelines remain decoupled so that the system can smoothly transition from basic deterministic routing to advanced local Large Language Model (LLM) tool calling.

---

## 🏗️ System Architecture

The codebase is structured around four core decoupled modules to ensure high maintainability and low systemic latency:

* **The Ear (Speech-to-Text):** Handles continuous background ambient listening. It utilizes `SpeechRecognition` to capture audio frames and translate them into clean text strings.
* **The Brain (Intent Parsing):** Currently maps user intents using deterministic keyword routing. Built structurally to adapt to a local LLM (via Ollama or Gemini API) utilizing structured function calling.
* **The Hands (OS Automation):** Integrates directly with the host operating system using native `subprocess` pipes and OS-level commands to execute actions without graphical dependency.
* **The Voice (Text-to-Speech):** An auditory feedback loop providing instant validation and state updates to the user.

---

## 🛠️ Tech Stack & Dependencies

* **Language:** Python 3.10+
* **Audio Capture & Processing:** `PyAudio`, `SpeechRecognition`
* **OS Level Interfacing:** `subprocess`, `os`

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone [https://github.com/MdFahimHassan/V.E.C.T.O.R.git](https://github.com/MdFahimHassan/V.E.C.T.O.R.git)
cd V.E.C.T.O.R.
```

### 2. Install Dependencies
Ensure your microphone system utilities are configured properly, then install the required Python libraries:
```bash
pip install SpeechRecognition pyaudio
```

> *Note on PyAudio:* If you experience installation errors on Windows systems, run `pip install pipwin` followed by `pipwin install pyaudio` to acquire the pre-compiled binary wheels.

### 3. Initialize the Router
Run the core engine script to start listening for commands:
```bash
python jarvis.py
```

---

## 🗺️ Project Roadmap

- [x] Establish core ambient listening pipeline (The Ear).
- [x] Map deterministic OS paths for launching primary applications (The Hands).
- [ ] Integrate a responsive local Text-to-Speech (TTS) audio layer (The Voice).
- [ ] Migrate the intent routing engine to an offline/API-driven LLM using **Function Calling** (The Brain).
- [ ] Add advanced GUI automation capabilities via mouse/keyboard mirroring controllers.
