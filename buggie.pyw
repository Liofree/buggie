"""Buggie: logcat, screenshot, screen recording and a bug report template for manual Android testing.
Standard library only. Start: double-click buggie.pyw or buggie.bat."""
import os, re, shutil, subprocess, time, webbrowser, tkinter as tk
from tkinter import ttk
from datetime import datetime

NAME = "Buggie"
ADB = shutil.which("adb") or r"C:\platform-tools\adb.exe"
RUNS_DIR = os.path.join(os.path.expanduser("~"), "Documents", f"{NAME} runs")
CONFIG_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), NAME)
WIFI_FILE = os.path.join(CONFIG_DIR, "last_wifi_address.txt")
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DEVICE_VIDEO = "/sdcard/buggie_rec.mp4"


def adb(*args, binary=False, timeout=30):
    r = subprocess.run([ADB, *args], capture_output=True, timeout=timeout, creationflags=NOWIN)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace").strip()


def stamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


class App:
    def __init__(self, root):
        self.root, self.video, self.info = root, None, {}
        self.paths = {"Log": "", "Screenshot": "", "Video": ""}
        root.title(NAME)
        self.status = tk.Label(root, anchor="w", font=("Segoe UI", 10, "bold"))
        self.status.pack(fill="x", padx=8, pady=4)

        z = tk.Frame(root); z.pack(fill="x", padx=8)
        tk.Label(z, text="Package:").pack(side="left")
        # List of installed apps (refreshed from the device when opened); typing works too
        self.package = ttk.Combobox(z, width=34, postcommand=self.load_packages)
        self.package.pack(side="left", padx=4)
        self.package.bind("<<ComboboxSelected>>", lambda e: self.package_selected())
        self.package.bind("<Return>", lambda e: self.package_selected())
        tk.Button(z, text="Current app", command=self.current_app).pack(side="left", padx=2)
        tk.Button(z, text="Read build info", command=self.read_info).pack(side="left", padx=2)
        tk.Button(z, text="🔌 Reconnect", command=self.reconnect).pack(side="left", padx=2)
        tk.Label(z, text="Run name:").pack(side="left", padx=(8, 0))
        self.run_name = tk.Entry(z, width=20); self.run_name.pack(side="left", padx=4)
        self.run_name.bind("<Return>", lambda e: self.new_run())
        tk.Button(z, text="New test run", command=self.new_run).pack(side="left", padx=2)

        # Wireless: phone > Developer options > Wireless debugging
        w = tk.Frame(root); w.pack(fill="x", padx=8, pady=(4, 0))
        tk.Label(w, text="Wi-Fi IP:port:").pack(side="left")
        self.wifi = tk.Entry(w, width=22); self.wifi.pack(side="left", padx=4)
        try:
            self.wifi.insert(0, open(WIFI_FILE, encoding="utf-8").read().strip())
        except OSError:
            pass
        tk.Label(w, text="Pairing code:").pack(side="left")
        self.code = tk.Entry(w, width=8); self.code.pack(side="left", padx=4)
        tk.Button(w, text="Pair (once)", command=self.pair).pack(side="left", padx=2)
        tk.Button(w, text="📶 Connect wireless", command=self.wifi_connect).pack(side="left", padx=2)
        tk.Button(w, text="Set up via cable", command=self.wifi_via_cable).pack(side="left", padx=2)

        k = tk.Frame(root); k.pack(fill="x", padx=8, pady=6)
        tk.Button(k, text="Clear log", width=14, command=self.clear_log).pack(side="left", padx=2)
        tk.Button(k, text="Save log", width=14, command=self.save_log).pack(side="left", padx=2)
        tk.Button(k, text="Screenshot", width=14, command=self.screenshot).pack(side="left", padx=2)
        self.vbutton = tk.Button(k, text="Start video", width=14, command=self.toggle_video)
        self.vbutton.pack(side="left", padx=2)
        tk.Button(k, text="📂 Open folder", width=16, font=("Segoe UI", 9, "bold"),
                  command=lambda: os.startfile(self.make_folder())).pack(side="left", padx=(12, 2))

        # Info box: read-only, but selectable and copyable
        self.auto = tk.Text(root, height=8, font=("Consolas", 9), bg="#f2f2f2")
        self.auto.pack(fill="x", padx=8)
        t = tk.Frame(root); t.pack(fill="x", padx=8, pady=(6, 0))
        tk.Label(t, text="Title:").pack(side="left")
        self.title = tk.Entry(t); self.title.insert(0, "[***] ")
        self.title.pack(side="left", fill="x", expand=True)
        tk.Button(t, text="Suggest title", command=self.suggest_title).pack(side="left")
        tk.Button(t, text="Copy title", command=lambda: self.clipboard(self.title.get())).pack(side="left")
        tk.Label(root, text="Bug report (edit right here):").pack(anchor="w", padx=8)
        self.report = tk.Text(root, height=18, wrap="word", undo=True)
        self.report.pack(fill="both", expand=True, padx=8)
        u = tk.Frame(root); u.pack(pady=6)
        tk.Button(u, text="Fill in device info", width=22, command=self.fill_template).pack(side="left", padx=2)
        tk.Button(u, text="Copy + save as TXT", width=30, command=self.copy_report).pack(side="left", padx=2)
        tk.Button(u, text="☕ Buy me a coffee", command=lambda: webbrowser.open("https://ko-fi.com/liofree")).pack(side="left", padx=(12, 2))

        self.new_run()
        self.read_info()
        self.fill_template()

    def message(self, text, error=False):
        self.status.config(text=text, fg="red" if error else "dark green")

    def ready(self):
        if not os.path.isfile(ADB):
            self.message(f"adb not found (PATH or {ADB}). Install Android SDK Platform-Tools.", True)
            return False
        try:
            if adb("get-state", timeout=5) != "device":
                self.message("No device connected (USB debugging on? Check adb devices).", True)
                return False
        except subprocess.TimeoutExpired:
            self.message("adb is not responding (device not authorized?).", True)
            return False
        return True

    def reconnect(self):
        """Restart the adb server, detect the device again, re-read the info."""
        if not os.path.isfile(ADB):
            return self.ready()
        self.message("Reconnecting …"); self.root.update()
        os.environ.pop("ANDROID_SERIAL", None)  # allow the cable again
        adb("kill-server", timeout=10)
        adb("start-server", timeout=20)
        time.sleep(2)  # the device needs a moment after the server starts
        if not self.ready() and self.wifi.get().strip():
            return self.wifi_connect()  # kill-server drops Wi-Fi, so connect again
        if self.ready():
            self.read_info(); self.fill_template()
            self.message(f"Connected: {self.info.get('Device', '')}")

    def pair(self):
        """Once: address and code from "Pair device with pairing code" on the phone."""
        # Look up the address on the local network; the phone may show a VPN address instead
        addr, code = self.mdns("pairing") or self.wifi.get().strip(), self.code.get().strip()
        if not (addr and code):
            return self.message("Keep the pairing dialog open on the phone and enter the 6-digit code.", True)
        try:
            out = adb("pair", addr, code, timeout=20)
        except subprocess.TimeoutExpired:
            out = ""
        if "Successfully paired" in out:
            self.wifi.delete(0, "end"); self.code.delete(0, "end")
            self.message("Paired. Now press Connect wireless (or enter IP:port from the Wireless debugging screen).")
        else:
            self.message(f"Pairing failed: {out or 'no response'}", True)

    def mdns(self, kind):
        """IP:port the phone announces on the network (kind: pairing or connect)."""
        try:
            m = re.search(rf"_adb-tls-{kind}\._tcp\.?\s+([\d.]+:\d+)", adb("mdns", "services", timeout=10))
        except subprocess.TimeoutExpired:
            return ""
        return m.group(1) if m else ""

    def wifi_via_cable(self):
        """Without pairing: with the cable plugged in, switch adbd to port 5555 (until the phone restarts)."""
        os.environ.pop("ANDROID_SERIAL", None)
        if not self.ready():
            return
        m = re.search(r"inet ([\d.]+)/", adb("shell", "ip", "-f", "inet", "addr", "show", "wlan0"))
        if not m:
            return self.message("The phone is not on Wi-Fi.", True)
        adb("tcpip", "5555"); time.sleep(3)
        self.wifi.delete(0, "end"); self.wifi.insert(0, f"{m.group(1)}:5555")
        self.wifi_connect(search=False)

    def wifi_connect(self, search=True):
        # Candidates: address found on the network (paired), then the entered/remembered one (e.g. :5555)
        candidates = [a for a in ((search and self.mdns("connect")), self.wifi.get().strip()) if a]
        if not candidates:
            return self.message("Pair first, or use Set up via cable.", True)
        self.message("Connecting wireless …"); self.root.update()
        for addr in dict.fromkeys(candidates):
            try:
                out = adb("connect", addr, timeout=15)
            except subprocess.TimeoutExpired:
                out = ""
            if "connected to" in out and "failed" not in out:  # also "already connected to"
                break
        else:
            return self.message(f"Wireless connection failed: {out or 'no response'}. Did you allow debugging on the phone?", True)
        self.wifi.delete(0, "end"); self.wifi.insert(0, addr)
        os.environ["ANDROID_SERIAL"] = addr  # send every command to this device, even with a cable attached
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(WIFI_FILE, "w", encoding="utf-8") as h:
            h.write(addr)
        if self.ready():
            self.read_info(); self.fill_template()
            self.message(f"Wireless connected: {self.info.get('Device', '')} ({addr})")

    def load_packages(self):
        """User apps on the device; typed text filters the list."""
        if not self.ready():
            return
        query = self.package.get().strip().lower()
        allp = sorted(z[8:] for z in adb("shell", "pm", "list", "packages", "-3").splitlines() if z.startswith("package:"))
        self.package["values"] = [p for p in allp if query in p.lower()] or allp

    def current_app(self):
        """Take the package of the app in the foreground."""
        if not self.ready():
            return
        fg = self.foreground()
        if not fg:
            return self.message("No app found in the foreground.", True)
        self.package.set(fg); self.package_selected()

    def package_selected(self):
        self.read_info(); self.fill_template()
        self.message(f"Package {self.package.get()}: version {self.info.get('App version', '')}")

    def new_run(self):
        # Remove characters Windows forbids, and trailing dots/spaces
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", self.run_name.get()).strip(" .")
        self.folder = os.path.join(RUNS_DIR, f"{stamp()}_{name}" if name else "Run_" + stamp())
        self.paths = dict.fromkeys(self.paths, "")
        self.show_auto()
        self.message(f"New test run: {self.folder}")

    def make_folder(self):
        # created on first save only, so no empty folders pile up
        os.makedirs(self.folder, exist_ok=True)
        return self.folder

    def file(self, kind, ext):
        return os.path.join(self.make_folder(), f"{kind}_{stamp()}.{ext}")

    def read_info(self):
        if not self.ready():
            return
        p = lambda k: adb("shell", "getprop", k)
        ver = self.version(self.package.get().strip())
        if not ver:  # package not installed: take the open app if it is a user app
            fg = self.foreground()
            if fg and f"package:{fg}" in adb("shell", "pm", "list", "packages", "-3").split():
                self.package.set(fg); ver = self.version(fg)
        if not ver:
            self.message("Package not installed: open the app on the phone and press Current app.", True)
        self.info = {"Device": p("ro.product.marketname") or p("ro.product.model"), "OS": "Android " + p("ro.build.version.release"),
                     "Security patch": p("ro.build.version.security_patch"),
                     "Build": p("ro.build.display.id"),
                     # Xiaomi HyperOS version (e.g. OS2.0.x.0.VOxxxx); other vendors: incremental
                     "OS build": p("ro.mi.os.version.incremental") or p("ro.build.version.incremental"),
                     "App version": ver or "[package not installed]"}
        self.show_auto()
        if ver:
            self.message("Build info read.")

    def version(self, package):
        if not package:
            return ""
        for line in adb("shell", "dumpsys", "package", package).splitlines():
            if "versionName=" in line:
                return line.split("versionName=")[1].strip()
        return ""

    def foreground(self):
        m = re.search(r"topResumedActivity=\S+ \S+ ([\w.]+)/", adb("shell", "dumpsys", "activity", "activities"))
        return m.group(1) if m else ""

    def show_auto(self):
        self.auto.config(state="normal"); self.auto.delete("1.0", "end")
        self.auto.insert("1.0", self.auto_text()); self.auto.config(state="disabled")

    def auto_text(self):
        z = [f"{k}: {v}" for k, v in self.info.items()]
        z.append("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
        z += [f"{k}: {v}" for k, v in self.paths.items() if v]
        return "\n".join(z)

    def clear_log(self):
        if self.ready():
            adb("logcat", "-c"); self.message("Log cleared.")

    def save_log(self):
        if self.ready():
            f = self.file("log", "txt")
            with open(f, "wb") as h:
                h.write(adb("logcat", "-d", binary=True, timeout=60))
            self.paths["Log"] = f; self.show_auto(); self.message(f"Log saved: {f}")

    def screenshot(self):
        if self.ready():
            f = self.file("screenshot", "png")
            with open(f, "wb") as h:
                h.write(adb("exec-out", "screencap", "-p", binary=True))
            self.paths["Screenshot"] = f; self.show_auto(); self.message(f"Screenshot: {f}")

    def toggle_video(self):
        if self.video is None:
            if not self.ready():
                return
            # screenrecord stops on its own on the device after 180 s
            self.video = subprocess.Popen([ADB, "shell", "screenrecord", DEVICE_VIDEO], creationflags=NOWIN)
            self.vbutton.config(text="Stop video", fg="red"); self.message("Recording (max. 3 min) …")
            return
        # stop the process on the device with SIGINT so the mp4 is finalized cleanly
        adb("shell", "pkill", "-INT", "screenrecord")
        try:
            self.video.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.video.kill()
        self.video = None
        self.vbutton.config(text="Start video", fg="black")
        time.sleep(1)
        f = self.file("video", "mp4")
        adb("pull", DEVICE_VIDEO, f, timeout=120)
        adb("shell", "rm", DEVICE_VIDEO)
        if os.path.isfile(f):
            self.paths["Video"] = f; self.show_auto(); self.message(f"Video: {f}")
        else:
            self.message("Could not fetch the video.", True)

    def header(self):
        i = self.info
        return {"Device and OS": f"{i.get('Device', '[device]')}, {i.get('OS', '[Android]')}",
                "OS build": i.get("OS build", "[build]"),
                "App version": i.get("App version", "[versionName]")}

    def fill_template(self):
        """Empty box: full template. Otherwise only the device lines are replaced, your text stays."""
        text = self.report.get("1.0", "end-1c")
        if not text.strip():
            text = ("Device and OS: \nOS build: \nApp version: \nNetwork: Wi-Fi\n"
                    "Location: \nReproducibility rate: 3/3\n\n"
                    "**Steps to reproduce:**\n1. \n\n**Expected result:**\n\n\n**Actual result:**\n")
        lines = text.split("\n")
        for n, z in enumerate(lines):
            for k, v in self.header().items():
                if z.startswith(k + ":"):
                    lines[n] = f"{k}: {v}"
        self.report.delete("1.0", "end"); self.report.insert("1.0", "\n".join(lines))

    def section(self, name):
        m = re.search(rf"\*\*{name}:\*\*\s*(.*?)(?=\n\*\*|\Z)", self.report.get("1.0", "end"), re.S)
        return m.group(1).strip() if m else ""

    def suggest_title(self):
        # simple rule (actual result + last step), no language model
        actual = re.split(r"(?<=[.!?])\s", self.section("Actual result"))[0].rstrip(".!? ")
        steps = [re.sub(r"^\d+[.)]\s*", "", z).strip() for z in self.section("Steps to reproduce").splitlines()]
        steps = [s for s in steps if s]
        if not actual:
            return self.message("Fill in Actual result first.", True)
        title = actual
        if steps:
            title += " when trying to " + steps[-1][0].lower() + steps[-1][1:].rstrip(".")
        if len(title) > 110:
            title = title[:110].rsplit(" ", 1)[0] + "…"
        # Area from the steps (last one first): "Go to Checkout" -> [Checkout]
        area = "***"
        for s in reversed(steps):
            b = re.search(r"\b(?:go to|navigate to|open|tap(?: on)?|select|in)\s+(?:the\s+)?([A-Za-z]+)", s, re.I)
            if b and b.group(1).lower() not in ("app", "application"):
                area = b.group(1).capitalize(); break
        self.title.delete(0, "end"); self.title.insert(0, f"[{area}] " + title)
        self.message("Title suggested, please check it.")

    def clipboard(self, text):
        self.root.clipboard_clear(); self.root.clipboard_append(text)
        self.message("Copied to clipboard.")

    def copy_report(self):
        text = self.report.get("1.0", "end-1c")
        title = self.title.get().strip()
        f = self.file("issue", "txt")  # one file per copy, nothing is overwritten
        with open(f, "w", encoding="utf-8") as h:
            h.write((f"# {title}\n\n" if title else "") + text + "\n")
        self.clipboard(text)
        self.message(f"Copied and saved: {f}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
