"""Quick UNIHIKER buzzer/audio hardware test.

Run this on the UNIHIKER:

    python tools/test_buzzer.py
"""

import shutil
import subprocess
import sys
import time


def list_audio_devices():
    print("\nAudio devices:")
    if not shutil.which("aplay"):
        print("- aplay not found; cannot list ALSA devices")
        return

    result = subprocess.run(
        ["aplay", "-l"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or result.stderr).strip()
    if output:
        print(output)
    else:
        print("- No ALSA playback devices reported")


def test_buzzer():
    print("Buzzer test:")
    if ".venv" in sys.executable:
        print(f"- Running inside virtualenv: {sys.executable}")
        print("- If Board().begin() hangs, use the UNIHIKER system PinPong instead:")
        print("  /usr/bin/python3 tools/test_buzzer.py")

    try:
        from pinpong.board import Board
    except ImportError as exc:
        print(f"- PinPong import failed: {exc}")
        print("- Run this on the UNIHIKER, where PinPong is normally preinstalled.")
        return False

    print("- Initializing board...")
    Board().begin()

    try:
        from pinpong.extension.unihiker import buzzer
    except ImportError as exc:
        print(f"- UNIHIKER buzzer import failed: {exc}")
        return False

    print("- Playing built-in tune...")
    tune = getattr(buzzer, "BA_DING", buzzer.DADADADUM)
    buzzer.play(tune, buzzer.Once)
    time.sleep(1.2)

    print("- Playing three tones...")
    for freq in (440, 660, 880):
        buzzer.pitch(freq, 1)
        time.sleep(0.25)

    try:
        buzzer.stop()
    except AttributeError:
        pass

    print("- Done. If you heard beeps, the onboard buzzer works.")
    return True


def main():
    print("UNIHIKER sound hardware check")
    buzzer_ok = test_buzzer()
    list_audio_devices()

    if not buzzer_ok:
        print("\nNo buzzer test was completed.")
    print("\nNote: the built-in device is a buzzer. Music/audio playback needs a USB or Bluetooth speaker.")


if __name__ == "__main__":
    main()
