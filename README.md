# Voice-Controlled Desktop Assistant

A Python-based desktop assistant that listens for voice commands, recognizes a wake word, and automates common tasks on Windows. It can launch supported applications, perform Google searches, and provide spoken feedback through text-to-speech.

## Features

- **Voice Activation:** Waits for a wake word such as "Hey Alex" or "Hey Alexa."
- **Speech Recognition:** Converts spoken commands into text using Google's speech recognition service.
- **Application Launching:** Opens supported desktop applications, including Steam, Discord, and Google Chrome.
- **Voice-Activated Search:** Performs Google searches using spoken queries.
- **Text-to-Speech:** Provides spoken responses and status updates.
- **Chrome Fallback:** Uses the default web browser if Chrome cannot be found in its usual installation locations.
- **Command Processing:** Uses regular expressions and predefined command mappings to identify and execute requests.

## Technologies Used

- **Python** — Core application logic and command processing
- **SpeechRecognition** — Voice input and speech recognition
- **PyAudio** — Microphone audio input
- **pyttsx3** — Text-to-speech output
- **Regular Expressions (`re`)** — Wake-word detection and command parsing
- **Windows Automation** — Application launching and process management

## Requirements

- Windows operating system
- Python installed
- A working microphone
- Internet connection for Google's speech recognition service
- Supported applications installed if you want to launch them

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Replace the repository URL with your own GitHub repository.

### 2. Install dependencies

```bash
pip install pyttsx3 SpeechRecognition pyaudio
```

If PyAudio fails to install, consult its installation instructions for your Python version and Windows environment.

### 3. Run the assistant

```bash
python assistant.py
```

The assistant waits briefly for startup, greets the user, calibrates the microphone for ambient noise, and begins listening for the wake word.

## Usage

After starting the program, say a wake word followed by a command.

| Voice command | Action |
|---|---|
| "Hey Alex, open Steam" | Opens Steam |
| "Hey Alex, open Discord" | Opens Discord |
| "Hey Alex, open Chrome" | Opens Google Chrome |
| "Hey Alex, search for Python tutorials" | Opens Google Search with the requested query |

You can also say the wake word first, wait for the assistant to respond, and then give your command.

After successfully executing a command, the assistant says "Task completed" and exits.

## How It Works

1. **Initialization:** Loads the speech recognition and text-to-speech libraries.
2. **Greeting:** Announces that the assistant is ready.
3. **Microphone Calibration:** Adjusts recognition settings for ambient noise.
4. **Wake-Word Detection:** Listens for the configured wake word.
5. **Command Recognition:** Converts the user's speech into text.
6. **Command Processing:** Matches the recognized text against supported application-launching and search commands.
7. **Execution and Feedback:** Performs the requested action, announces the result, and exits after a successful command.

## Project Structure

```text
desktop-assistant/
├── assistant.py
└── README.md
```

## Current Limitations

- Supports a predefined set of commands rather than unrestricted natural-language requests.
- Uses Google's online speech recognition service, so speech recognition is not fully offline.
- Currently exits after the first successfully executed command.
- Application launching relies on Windows-specific behavior and installation paths.
- Does not currently integrate a large language model or maintain conversational memory.

## Future Improvements

- Add support for multiple commands in a single session.
- Integrate a large language model for more flexible natural-language interactions.
- Add configurable application mappings.
- Implement local speech recognition for improved offline functionality.
- Add command history, logging, and automated tests.
- Introduce a settings file for user preferences and wake-word configuration.

## Learning Outcomes

This project explores Python application development, speech recognition, audio input, text-to-speech, regular expressions, subprocess management, and Windows desktop automation.

## License

Choose a license before distributing this project publicly. For example, the MIT License allows others to use, modify, and distribute the software under its terms.
