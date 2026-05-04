"""Quick UNIHIKER buzzer/audio hardware test.

Run this on the UNIHIKER, not on the development PC:

    python3 tools/test_buzzer.py
"""

import os
import shutil
import subprocess
import sys
import time


def print_runtime():
    print(f"Python: {sys.executable}")
    print(f"Version: {sys.version.split()[0]}")


def probe_system_pinpong():
    system_python = "/usr/bin/python3"
    if os.name == "nt" or not os.path.exists(system_python):
        return
    if os.path.realpath(sys.executable) == os.path.realpath(system_python):
        return

    result = subprocess.run(
        [
            system_python,
            "-c",
            "import pinpong; import sys; print(sys.executable)",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"- PinPong exists in system Python: {result.stdout.strip()}")
        print("- Try: python3 tools/test_buzzer.py")
    else:
        print("- PinPong was not found in /usr/bin/python3 either.")


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


def test_alsa_tone():
    print("\nALSA playback tone:")
    if not shutil.which("speaker-test"):
        print("- speaker-test not found; skipping playback tone")
        return

    print("- Playing 440 Hz for 1 second on default ALSA device...")
    try:
        result = subprocess.run(
            ["speaker-test", "-t", "sine", "-f", "440", "-l", "1"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        print("- speaker-test timed out")
        return

    if result.returncode == 0:
        print("- Done. If you heard a tone, ALSA playback works.")
        return

    output = (result.stderr or result.stdout).strip()
    print("- speaker-test failed")
    if output:
        print(output)


def test_buzzer():
    print("Buzzer test:")
    try:
        from pinpong.board import Board
        from pinpong.extension.unihiker import buzzer
    except ImportError as exc:
        print(f"- PinPong import failed: {exc}")
        print("- If you used uv run, it may be hiding system packages inside .venv.")
        probe_system_pinpong()
        return False

    print("- Initializing board...")
    Board().begin()

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
    print_runtime()
    buzzer_ok = test_buzzer()
    list_audio_devices()
    test_alsa_tone()

    if not buzzer_ok:
        print("\nNo buzzer test was completed.")
    print("\nNote: the built-in device is a buzzer. Music/audio playback needs a USB or Bluetooth speaker.")


if __name__ == "__main__":
    main()
