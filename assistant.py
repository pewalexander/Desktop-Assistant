"""
Alex - a voice assistant for your laptop
----------------------------------------
1. First run: asks your name (by voice, with a typing box as backup) and remembers it.
2. At start-up it greets you: "Welcome <your name>".
3. Say "Hey Alex" and then a command:
     - "open steam" / "open discord" / "open chrome"
     - "search for <anything>"  (opens Google Search in Chrome)
   If an app isn't installed, it tells you instead of failing silently.
4. Says "Task completed", then keeps listening for the next "Hey Alex".
   Say "Hey Alex, change my name" to redo the name setup.
   Say "Hey Alex, quit" to shut it down.

Install once:  pip install pyttsx3 SpeechRecognition pyaudio
Note: speech recognition uses Google's free web API, so it needs internet.
"""

import json
import os
import random
import re
import subprocess
import time
import urllib.parse
import webbrowser

import pyttsx3
import speech_recognition as sr

ASSISTANT_NAME = "Alex"  # the name you say to wake it: "Hey Alex"
# Speech recognition often mishears names, so accept close variants too.
WAKE_NAMES = r"alex\w*|alix|alec|aleck"
WAKE_PATTERN = rf"\b(?:(?:hey|hi|okay|ok)\s+)?(?:{WAKE_NAMES})\b"

# Background-noise tuning: raise this (e.g. 1.6, 2.0) if it keeps listening
# after you finish speaking; lower it (e.g. 1.0) if it misses quiet speech.
NOISE_BOOST = 1.4

# Where the user's name is remembered (one file per Windows account)
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AlexAssistant")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


# ---------------------------------------------------------------- speaking
def speak(text):
    """Say text out loud (and print it)."""
    print(f"Assistant: {text}")
    try:
        engine = pyttsx3.init()  # fresh engine each time avoids pyttsx3 hang bugs
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"(speech error: {e})")


# ---------------------------------------------------------------- finding installed apps
def _exe_from_command(command):
    """Pull the program path out of a registry command like: "C:\\x\\app.exe" --flag "%1"."""
    command = (command or "").strip()
    if command.startswith('"'):
        end = command.find('"', 1)
        return command[1:end] if end > 0 else None
    return command.split(" ")[0] if command else None


def _protocol_exe(scheme):
    """Program Windows uses for links like steam:// or discord://, if it still exists."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{scheme}\shell\open\command") as key:
            command = winreg.QueryValue(key, "")
    except (OSError, ImportError):
        return None
    exe = _exe_from_command(command)
    return exe if exe and os.path.exists(exe) else None


def _app_paths_exe(exe_name):
    """Look up a program in Windows' 'App Paths' registry list."""
    try:
        import winreg
    except ImportError:
        return None
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}") as key:
                path = winreg.QueryValue(key, "").strip('"')
        except OSError:
            continue
        if path and os.path.exists(path):
            return path
    return None


# ---------------------------------------------------------------- Chrome
def find_chrome():
    candidates = [
        os.path.join(os.environ.get("ProgramFiles", ""), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return _app_paths_exe("chrome.exe")


def chrome_installed():
    return find_chrome() is not None


def open_chrome(url=None):
    chrome = find_chrome()
    if chrome:
        subprocess.Popen([chrome] + ([url] if url else []))
    else:
        # Chrome isn't installed: fall back to the default browser
        webbrowser.open(url or "https://www.google.com")


# ---------------------------------------------------------------- Steam
def steam_installed():
    if _protocol_exe("steam"):
        return True
    for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", "")):
        if base and os.path.exists(os.path.join(base, "Steam", "steam.exe")):
            return True
    return False


def open_steam():
    os.startfile("steam://open/main")


# ---------------------------------------------------------------- Discord
def _discord_update_exe():
    return os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Discord\Update.exe")


def discord_installed():
    return os.path.exists(_discord_update_exe()) or bool(_protocol_exe("discord"))


def open_discord():
    update_exe = _discord_update_exe()
    if os.path.exists(update_exe):
        subprocess.Popen([update_exe, "--processStart", "Discord.exe"])
    else:
        subprocess.Popen([_protocol_exe("discord")])


# ---------------------------------------------------------------- Epic Games
def epic_installed():
    if _protocol_exe("com.epicgames.launcher"):
        return True
    for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", "")):
        if base and os.path.exists(os.path.join(
                base, "Epic Games", "Launcher", "Portal", "Binaries", "Win32", "EpicGamesLauncher.exe")):
            return True
    return False


def open_epic():
    os.startfile("com.epicgames.launcher://apps")


# ---------------------------------------------------------------- any other app (generic lookup)
def find_app_shortcut(spoken_name):
    """Look for a Start Menu shortcut whose name matches what you said. Returns its path or None."""
    wanted = re.sub(r"[^a-z0-9]", "", spoken_name.lower())
    if not wanted:
        return None
    start_menus = [
        os.path.join(os.environ.get("ProgramData", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    ]
    for folder in start_menus:
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if not f.lower().endswith(".lnk"):
                    continue
                shortcut = re.sub(r"[^a-z0-9]", "", os.path.splitext(f)[0].lower())
                if shortcut and (wanted == shortcut or wanted in shortcut):
                    return os.path.join(root, f)
    return None


# Add more apps here:  (spoken names, name to say out loud, "is it installed?" check, launch function)
APPS = [
    (["steam"], "Steam", steam_installed, open_steam),
    (["epic games", "epic game", "epic launcher", "epic"], "Epic Games", epic_installed, open_epic),
    (["discord"], "Discord", discord_installed, open_discord),
    (["google chrome", "chrome", "google"], "Chrome", chrome_installed, open_chrome),
]
APP_LABELS = ", ".join(app[1] for app in APPS)


# ---------------------------------------------------------------- commands
def handle_command(command):
    """
    Returns:
      True  - the command was carried out
      False - the command wasn't understood
      None  - understood but couldn't be done (the reason was already spoken)
    """
    command = command.lower().strip()
    print(f"Command: {command}")

    # strip polite filler: "please", "can you", "could you", ...
    command = re.sub(r"^(?:(?:please|can you|could you|would you|go ahead and)\s+)+", "", command)

    search_words = r"\b(?:search|look\s+up|look\s+for|find)\b"
    open_only = re.match(r"^(?:open|launch|start)\b", command) and not re.search(search_words, command)

    # --- search: "search for X", "search google for X", "google X",
    #     "look up X", "find X", "open chrome and search X", ...
    m = None if open_only else re.search(
        r"\b(?:search|google|look\s+up|look\s+for|find)\b"
        r"(?:\s+(?:up|for|on|in|me|google|chrome|the\s+web|the\s+internet|online))*\s+(.+)",
        command,
    )
    if m:
        query = m.group(1).strip()
        query = re.sub(r"\s+(?:on|in|using|with)\s+(?:google|chrome)$", "", query).strip()
        if query:
            url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
            open_chrome(url)
            return True

    # --- open an app
    if re.match(r"^(?:open|launch|start)\b", command):
        for names, label, is_installed, launch in APPS:
            if any(name in command for name in names):
                if not is_installed():
                    speak(f"I can't open {label} because it doesn't look like it's installed "
                          f"on this computer. You'll need to download it first.")
                    return None
                try:
                    launch()
                    return True
                except Exception as e:
                    print(f"Could not open {label}: {e}")
                    speak(f"Sorry, something went wrong while opening {label}.")
                    return None

        # Not one of the built-in apps: treat whatever was said after "open" as an app name
        app_name = re.sub(r"^(?:open|launch|start)\s+(?:up\s+)?(?:the\s+)?", "", command).strip()
        app_name = re.sub(r"\s+(?:app|application|launcher|please)$", "", app_name).strip()
        if app_name:
            shortcut = find_app_shortcut(app_name)
            if shortcut:
                try:
                    os.startfile(shortcut)
                    return True
                except Exception as e:
                    print(f"Could not open {app_name}: {e}")
                    speak(f"Sorry, something went wrong while opening {app_name}.")
                    return None
            speak(f"I can't open {app_name} because it doesn't look like it's installed "
                  f"on this computer. You'll need to download it first.")
            return None

    return False


# ---------------------------------------------------------------- listening
recognizer = sr.Recognizer()


def quick_calibrate(mic, seconds=0.5):
    """Re-measure background noise so the end of your speech is detected quickly."""
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=seconds)
    recognizer.energy_threshold *= NOISE_BOOST


def listen(mic, timeout=None, phrase_limit=8):
    """Listen once. Returns lowercase text, or '' if nothing understood."""
    with mic as source:
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            return ""
    try:
        text = recognizer.recognize_google(audio).lower()
        print(f"Heard: {text}")
        return text
    except sr.UnknownValueError:
        print("Heard something, but couldn't make out words.")
        return ""
    except sr.RequestError as e:
        print(f"(speech service unreachable - check internet: {e})")
        return ""


# ---------------------------------------------------------------- remembering the user's name
def load_name():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("name") or None
    except (OSError, ValueError):
        return None


def save_name(name):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"name": name}, f)
    except OSError as e:
        print(f"(couldn't save name: {e})")


def clean_name(text):
    """'my name is maria' -> 'Maria'. Returns '' if it doesn't look like a name."""
    text = (text or "").lower().strip()
    text = re.sub(r"^(?:my name is|my name's|i am|i'm|im|it's|its|this is|call me|you can call me)\s+", "", text)
    text = re.sub(r"[^a-z' -]", "", text).strip()
    if not text or len(text.split()) > 3:
        return ""
    return text.title()


def ask_name_by_typing():
    """Pop up a small box to type a name (works even when there's no console window)."""
    try:
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        answer = simpledialog.askstring(f"{ASSISTANT_NAME} setup", "What's your name?", parent=root)
        root.destroy()
        return clean_name(answer or "")
    except Exception as e:
        print(f"(typing box unavailable: {e})")
        return ""


def setup_name(mic):
    """Ask for the user's name by voice (up to 3 tries), confirm it, else fall back to typing."""
    for attempt in range(3):
        if attempt == 0:
            speak(f"Hi, I'm {ASSISTANT_NAME}, your assistant. What's your name?")
        else:
            speak("Sorry, what's your name?")
        quick_calibrate(mic)
        name = clean_name(listen(mic, timeout=8, phrase_limit=5))
        if not name:
            continue
        speak(f"Did you say {name}? Say yes or no.")
        quick_calibrate(mic)
        answer = listen(mic, timeout=6, phrase_limit=3)
        if re.search(r"\b(?:yes|yeah|yep|yup|correct|right|sure)\b", answer):
            return name
    speak("I'll let you type it instead.")
    return ask_name_by_typing()


# ---------------------------------------------------------------- main
def main():
    time.sleep(5)  # give Windows a moment to finish logging in / audio to start

    try:
        mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
    except (OSError, AttributeError) as e:
        print(f"No usable microphone: {e}")
        speak("I can't find a microphone on this computer, so I can't listen.")
        return
    recognizer.energy_threshold *= NOISE_BOOST
    recognizer.dynamic_energy_threshold = False  # keep the noise level steady over hours of running
    recognizer.pause_threshold = 0.7  # silence that ends a phrase (lower = faster, higher = more patient)

    user_name = load_name()
    if not user_name:
        user_name = setup_name(mic)
        if user_name:
            save_name(user_name)
        else:
            user_name = "friend"  # not saved, so it asks again next time

    speak(random.choice([
        f"Welcome {user_name}. Say Hey {ASSISTANT_NAME} when you need me.",
        f"Welcome back, {user_name}. What can I open for you?",
        f"Hello {user_name}, welcome back. Say Hey {ASSISTANT_NAME} to give me a command.",
    ]))
    print(f"Listening for 'Hey {ASSISTANT_NAME}'... (everything I hear will print here)")

    while True:
        heard = listen(mic, timeout=None, phrase_limit=6)  # waits for the wake word
        if not heard or not re.search(WAKE_PATTERN, heard):
            continue

        # "Hey Alex open steam" in one breath
        command = re.sub(WAKE_PATTERN, "", heard, count=1).strip()
        if not command:
            speak("Yes?")
            quick_calibrate(mic)  # re-check background noise right before the command
            command = listen(mic, timeout=6, phrase_limit=6)

        if not command:
            speak("I didn't catch that.")
            continue

        # "Hey Alex, quit" shuts the assistant down completely
        if re.search(r"\b(?:quit|exit|shut down|stop listening|goodbye)\b", command):
            speak("Goodbye")
            break

        # "Hey Alex, change my name"
        if re.search(r"\b(?:change|reset|update)\b.*\bname\b", command):
            new_name = setup_name(mic)
            if new_name:
                save_name(new_name)
                speak(f"Nice to meet you, {new_name}. Task completed")
            quick_calibrate(mic)
            print(f"Listening for 'Hey {ASSISTANT_NAME}'...")
            continue

        result = handle_command(command)
        if result is True:
            speak("Task completed")
        elif result is False:
            speak(f"Sorry, I can only open {APP_LABELS}, or search Google.")
        # result is None: the problem was already explained out loud

        quick_calibrate(mic)  # reset noise level, then wait for the next "Hey Alex"
        print(f"Listening for 'Hey {ASSISTANT_NAME}'...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
