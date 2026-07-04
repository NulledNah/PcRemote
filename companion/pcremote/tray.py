import os
import sys
import threading
import time
from datetime import datetime


def _find_icon_path():
    candidates = []
    try:
        base = getattr(sys, '_MEIPASS', '')
        if base:
            candidates.append(os.path.join(base, 'icon.ico'))
    except Exception:
        pass
    candidates.append(os.path.join(os.path.dirname(__file__), '..', 'icon.ico'))
    candidates.append(os.path.join(os.path.dirname(sys.executable), 'icon.ico'))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _load_image():
    icon_path = _find_icon_path()
    if icon_path:
        try:
            from PIL import Image
            return Image.open(icon_path)
        except Exception:
            pass

    from PIL import Image, ImageDraw
    img = Image.new('RGB', (64, 64), color='#1a73e8')
    draw = ImageDraw.Draw(img)
    draw.rectangle([16, 20, 48, 44], fill='white')
    draw.polygon([(30, 44), (50, 32), (50, 56)], fill='white')
    return img


def _get_log_path():
    from .config import get_data_dir
    return os.path.join(get_data_dir(),
                        f"pcremote-{datetime.now():%Y%m%d}.log")


class DashboardWindow:
    def __init__(self, connection_url: str):
        self._url = connection_url
        self._root = None
        self._ready = threading.Event()
        self._show_event = threading.Event()
        self._close_flag = threading.Event()
        self._logs_visible = False
        self._log_text = None
        self._log_pos = 0
        self._thread = None

    def _create(self):
        import tkinter as tk
        import qrcode
        from PIL import Image, ImageTk, ImageDraw

        BG = '#EBE0D3'
        ACCENT = '#7F5A49'
        ACCENT_DARK = '#6B493A'
        CREAM = '#FDF0D9'
        LOG_BG = '#3B2A22'
        LOG_FG = '#EBE0D9'

        self._root = tk.Tk()
        self._root.title("PcRemote Dashboard")
        self._root.configure(bg=BG)
        self._root.resizable(True, True)
        self._root.minsize(400, 300)
        self._root.withdraw()

        icon_path = _find_icon_path()
        if icon_path:
            try:
                self._root.iconbitmap(icon_path)
            except Exception:
                pass

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        outer = tk.Frame(self._root, bg=BG)
        outer.grid(row=0, column=0, sticky='nsew', padx=15, pady=15)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        left_frame = tk.Frame(outer, bg=BG)
        left_frame.grid(row=0, column=0, sticky='nw')

        qr = qrcode.QRCode(box_size=6, border=3)
        qr.add_data(self._url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=ACCENT_DARK, back_color=CREAM)
        img = img.resize((220, 220), Image.NEAREST)
        photo = ImageTk.PhotoImage(img)

        qr_label = tk.Label(left_frame, image=photo, bg=CREAM)
        qr_label.image = photo
        qr_label.pack()

        url_label = tk.Label(
            left_frame, text=self._url, bg=BG, fg=ACCENT_DARK,
            font=("Consolas", 10)
        )
        url_label.pack(pady=(8, 0))

        self._log_frame = tk.Frame(outer, bg=BG)
        scrollbar = tk.Scrollbar(self._log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._log_text = tk.Text(
            self._log_frame,
            bg=LOG_BG, fg=LOG_FG,
            font=("Consolas", 9),
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            insertbackground=LOG_FG,
            borderwidth=0,
            padx=8, pady=8,
        )
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._log_text.yview)

        bottom_frame = tk.Frame(self._root, bg=BG)
        bottom_frame.grid(row=1, column=0, sticky='ew', padx=15, pady=(0, 10))

        self._toggle_btn = tk.Button(
            bottom_frame, text="Show Logs",
            bg=ACCENT, fg=CREAM,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            activebackground=ACCENT_DARK,
            activeforeground=CREAM,
            cursor='hand2',
            padx=16, pady=4,
            borderwidth=0,
        )
        self._toggle_btn.pack(side=tk.LEFT)

        def _on_toggle():
            self._logs_visible = not self._logs_visible
            self._toggle_btn.configure(
                text="Hide Logs" if self._logs_visible else "Show Logs"
            )
            self._update_log_visibility()

        self._toggle_btn.configure(command=_on_toggle)

        self._poll_logs()
        self._ready.set()

    def _poll_logs(self):
        import tkinter as tk
        if self._close_flag.is_set():
            return
        if self._logs_visible and self._log_text is not None:
            log_path = _get_log_path()
            if os.path.isfile(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        f.seek(self._log_pos)
                        new_data = f.read()
                        if new_data:
                            self._log_text.insert(tk.END, new_data)
                            self._log_text.see(tk.END)
                            self._log_pos = f.tell()
                except Exception:
                    pass
        if self._root:
            self._root.after(1000, self._poll_logs)

    def _update_log_visibility(self):
        if self._log_frame is None:
            return
        if self._logs_visible:
            self._log_frame.grid(row=0, column=1, sticky='nsew', padx=(15, 0))
            self._log_pos = 0
        else:
            self._log_frame.grid_forget()

    def _on_close(self):
        self.hide()

    def _run(self):
        import tkinter as tk
        try:
            self._create()
            while not self._close_flag.is_set():
                try:
                    if self._show_event.wait(timeout=0.1):
                        self._show_event.clear()
                        if self._root:
                            self._root.deiconify()
                            self._root.lift()
                            self._root.attributes('-topmost', True)
                            self._root.after(200,
                                lambda: self._root.attributes('-topmost', False))
                    if self._root:
                        self._root.update()
                except tk.TclError:
                    break
        except Exception:
            pass

    def show(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self._ready.wait(timeout=3)
        self._show_event.set()

    def hide(self):
        self._show_event.clear()
        if self._root:
            try:
                self._root.withdraw()
            except Exception:
                pass

    def close(self):
        self._close_flag.set()
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass


def run_tray(on_stop_server, on_start_server, on_quit,
             on_init=None, get_connection_url=None):
    if os.name != 'nt':
        return False

    try:
        from pystray import Icon as TrayIcon, Menu, MenuItem
    except ImportError:
        return False

    image = _load_image()
    get_connection_url = get_connection_url or (lambda: "")
    state = {"running": True, "dashboard": None}

    def do_dashboard(icon, item):
        if state["dashboard"] is None:
            url = get_connection_url()
            state["dashboard"] = DashboardWindow(url)
        state["dashboard"].show()

    def do_stop(icon, item):
        if state["running"]:
            on_stop_server()
            state["running"] = False
            icon.menu = _build_menu(state, do_dashboard, do_stop, do_start, do_quit)
            icon.update_menu()

    def do_start(icon, item):
        if not state["running"]:
            on_start_server()
            state["running"] = True
            icon.menu = _build_menu(state, do_dashboard, do_stop, do_start, do_quit)
            icon.update_menu()

    def do_quit(icon, item):
        if state["running"]:
            on_stop_server()
            state["running"] = False
        if state["dashboard"]:
            state["dashboard"].close()
        icon.stop()
        on_quit()

    def setup(icon):
        icon.visible = True
        if on_init:
            on_init()

    menu = _build_menu(state, do_dashboard, do_stop, do_start, do_quit)
    icon = TrayIcon("PcRemote", image, menu=menu)
    icon.run(setup)
    return True


def _build_menu(state, do_dashboard, do_stop, do_start, do_quit):
    from pystray import Menu, MenuItem
    items = [
        MenuItem("Show Dashboard", do_dashboard, default=True),
        Menu.SEPARATOR,
    ]
    if state["running"]:
        items.append(MenuItem("Stop Server", do_stop))
    else:
        items.append(MenuItem("Start Server", do_start))
    items.append(Menu.SEPARATOR)
    items.append(MenuItem("Quit", do_quit))
    return Menu(*items)
