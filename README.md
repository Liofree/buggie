# Buggie

*Quiet tools. Real impact.* — a small, free Windows tool by [Liofree](https://liofree.com).

Buggie helps you write Android bug reports during manual testing. Connect a phone over USB or Wi-Fi,
capture what you need with one click, and get a ready-to-paste report with the device details filled in.

[![Buy me a coffee](https://img.shields.io/badge/Ko--fi-Buy%20me%20a%20coffee-ff5e5b?logo=ko-fi&logoColor=white)](https://ko-fi.com/liofree)

## What it does

- **Connect** – USB, wireless pairing with a code (Android 11+), wireless connect with automatic
  address lookup, or *Set up via cable* (port 5555, no pairing needed). *Reconnect* restarts adb if it hangs.
- **Pick the app** – choose from the installed apps, or press *Current app* to take whatever is open on the phone.
- **Device info** – model, Android version, security patch, build and app version are read automatically.
- **Capture** – clear and save logcat, take screenshots, record the screen (up to 3 minutes).
  Everything of one test run goes into its own folder under `Documents\Buggie runs`.
- **Bug report** – a template with *Steps to reproduce*, *Expected result* and *Actual result*.
  *Fill in device info* updates the device lines without touching your text,
  *Suggest title* builds a title from the actual result and the last step,
  *Copy + save as TXT* puts the report on the clipboard and keeps a copy in the run folder.
- **Nothing leaves your PC.** No account, no telemetry, no network access except adb to your phone.

## Requirements

- Windows with [Python 3](https://www.python.org/downloads/) (tkinter is included in the standard installer)
- [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) –
  `adb` on your PATH, or unpacked to `C:\platform-tools`
- On the phone: *Developer options → USB debugging* (and *Wireless debugging* for Wi-Fi)

## Start

Download or clone this repository and double-click `buggie.bat` (or `buggie.pyw`).
No installation, no dependencies beyond the Python standard library.

The last wireless address is remembered in `%APPDATA%\Buggie`.

## Support

Buggie is free. If it saves you time, you can [buy me a coffee on Ko-fi](https://ko-fi.com/liofree).

## License

[MIT](LICENSE) © 2026 Liofree
