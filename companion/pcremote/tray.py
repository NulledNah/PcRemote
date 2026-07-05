import os
import sys
import threading
import time
import tkinter as tk
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
    def __init__(self, connection_url: str, server_running: bool = True,
                 on_toggle_server=None):
        self._url = connection_url
        self._server_running = server_running
        self._toggle_server_callback = on_toggle_server
        self._dark_mode = True
        self._root = None
        self._ready = threading.Event()
        self._show_event = threading.Event()
        self._close_flag = threading.Event()
        self._logs_visible = False
        self._log_text = None
        self._log_pos = 0
        self._thread = None
        self._qr_light = None
        self._qr_dark = None
        self._qr_label = None
        self._url_label = None
        self._log_frame = None
        self._outer_frame = None
        self._content_frame = None
        self._bar_frame = None
        self._bottom_frame = None
        self._toggle_btn = None
        self._dark_btn = None
        self._clear_btn = None
        self._copy_btn = None
        self._server_btn = None
        self._bar_label = None

    @property
    def dark_mode(self):
        return self._dark_mode

    @dark_mode.setter
    def dark_mode(self, value):
        self._dark_mode = value
        if self._root:
            self._apply_theme()

    def _colors(self):
        if self._dark_mode:
            return {
                'bg': '#1A1210', 'fg': '#EBE0D3',
                'accent': '#D4A88C', 'accent_dark': '#8B6B5A',
                'cream': '#3B2A22', 'log_bg': '#2B1A14',
                'log_fg': '#C4B5A5', 'btn_bg': '#D4A88C',
                'btn_fg': '#3B2A22', 'bar_bg': '#241914',
            }
        else:
            return {
                'bg': '#EBE0D3', 'fg': '#3B2A22',
                'accent': '#7F5A49', 'accent_dark': '#6B493A',
                'cream': '#FDF0D9', 'log_bg': '#3B2A22',
                'log_fg': '#EBE0D9', 'btn_bg': '#7F5A49',
                'btn_fg': '#FDF0D9', 'bar_bg': '#E5D9CA',
            }

    def _make_qr_images(self):
        import qrcode
        from PIL import Image, ImageTk

        for mode, fill, back in [
            ('light', '#6B493A', '#FDF0D9'),
            ('dark', '#D4A88C', '#3B2A22'),
        ]:
            qr = qrcode.QRCode(box_size=6, border=3)
            qr.add_data(self._url)
            qr.make(fit=True)
            img = qr.make_image(fill_color=fill, back_color=back)
            img = img.resize((220, 220), Image.NEAREST)
            photo = ImageTk.PhotoImage(img, master=self._root)
            if mode == 'light':
                self._qr_light = photo
            else:
                self._qr_dark = photo

    def _apply_theme(self):
        c = self._colors()

        self._root.configure(bg=c['bg'])

        for widget in [
            self._outer_frame, self._content_frame,
            self._bottom_frame, self._qr_frame,
        ]:
            if widget:
                widget.configure(bg=c['bg'])

        if self._bar_frame:
            self._bar_frame.configure(bg=c['bar_bg'])

        if self._bar_label:
            self._bar_label.configure(bg=c['bar_bg'], fg=c['fg'])

        if self._qr_label:
            self._qr_label.configure(
                image=self._qr_dark if self._dark_mode else self._qr_light,
                bg=c['cream']
            )

        if self._url_label:
            self._url_label.configure(bg=c['bg'], fg=c['accent_dark'])

        if self._log_text:
            self._log_text.configure(bg=c['log_bg'], fg=c['log_fg'],
                                     insertbackground=c['log_fg'])

        for btn, disabled_fg in [
            (self._toggle_btn, None),
            (self._server_btn, c['btn_fg']),
            (self._dark_btn, None),
            (self._clear_btn, None),
            (self._copy_btn, None),
        ]:
            if btn:
                kw = dict(bg=c['btn_bg'], fg=c['btn_fg'],
                          activebackground=c['accent_dark'],
                          activeforeground=c['btn_fg'])
                if disabled_fg:
                    kw['disabledforeground'] = disabled_fg
                btn.configure(**kw)

    def _on_toggle_dark(self):
        self._dark_mode = not self._dark_mode
        self._dark_btn.configure(
            text="Light Mode" if self._dark_mode else "Dark Mode"
        )
        self._apply_theme()

    def _on_toggle_server(self):
        if self._toggle_server_callback:
            self._server_btn.configure(state="disabled",
                                       text="Stopping..." if self._server_running else "Starting...")
            self._toggle_server_callback()
            self._server_running = not self._server_running
            self._root.after(1500, self._update_server_button)

    def _update_server_button(self):
        self._server_btn.configure(
            state="normal",
            text="Stop Server" if self._server_running else "Start Server"
        )

    def _on_toggle_logs(self):
        self._logs_visible = not self._logs_visible
        self._toggle_btn.configure(
            text="Hide Logs" if self._logs_visible else "Show Logs"
        )
        self._update_log_visibility()

    def _on_clear_log(self):
        if self._log_text:
            self._log_text.delete("1.0", tk.END)
            log_path = _get_log_path()
            if os.path.isfile(log_path):
                self._log_pos = os.path.getsize(log_path)

    def _on_copy_log(self):
        if self._log_text:
            content = self._log_text.get("1.0", tk.END)
            self._root.clipboard_clear()
            self._root.clipboard_append(content.rstrip('\n'))

    def _create(self):
        c = self._colors()

        self._root = tk.Tk()
        self._root.title("PcRemote Dashboard")
        self._root.configure(bg=c['bg'])
        self._root.resizable(True, True)
        self._root.withdraw()

        self._make_qr_images()

        icon_path = _find_icon_path()
        if icon_path:
            try:
                self._root.iconbitmap(icon_path)
            except Exception:
                pass

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        self._outer_frame = tk.Frame(self._root, bg=c['bg'])
        self._outer_frame.grid(row=0, column=0, sticky='nsew', padx=12, pady=12)
        self._outer_frame.columnconfigure(0, weight=1)

        # --- top bar: server button ---
        self._bar_frame = tk.Frame(self._outer_frame, bg=c['bar_bg'])
        self._bar_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        self._bar_frame.columnconfigure(0, weight=1)

        server_label = tk.Label(
            self._bar_frame, text="PcRemote Server",
            bg=c['bar_bg'], fg=c['fg'],
            font=("Segoe UI", 9, "bold"),
        )
        self._bar_label = server_label
        server_label.grid(row=0, column=0, sticky='w', padx=(8, 0), pady=4)

        self._server_btn = tk.Button(
            self._bar_frame,
            text="Stop Server" if self._server_running else "Start Server",
            bg=c['btn_bg'], fg=c['btn_fg'],
            disabledforeground=c['btn_fg'],
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            activebackground=c['accent_dark'],
            activeforeground=c['btn_fg'],
            cursor='hand2',
            padx=10, pady=2,
            borderwidth=0,
            command=self._on_toggle_server,
        )
        self._server_btn.grid(row=0, column=1, sticky='e', padx=(0, 8), pady=4)

        # --- content area ---
        self._content_frame = tk.Frame(self._outer_frame, bg=c['bg'])
        self._content_frame.grid(row=1, column=0, sticky='nsew')
        self._outer_frame.rowconfigure(1, weight=1)
        self._content_frame.columnconfigure(0, weight=1)
        self._content_frame.rowconfigure(0, weight=1)

        # QR + URL label
        self._qr_frame = tk.Frame(self._content_frame, bg=c['bg'])
        self._qr_frame.grid(row=0, column=0, sticky='')

        self._qr_label = tk.Label(
            self._qr_frame,
            image=self._qr_dark, bg=c['cream']
        )
        self._qr_label.pack()

        self._url_label = tk.Label(
            self._qr_frame, text=self._url,
            bg=c['bg'], fg=c['accent_dark'],
            font=("Consolas", 10),
        )
        self._url_label.pack(pady=(8, 0))

        # log panel (column 1, hidden by default)
        self._log_frame = tk.Frame(self._content_frame, bg=c['bg'])
        self._content_frame.columnconfigure(1, weight=1)

        scrollbar = tk.Scrollbar(self._log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._log_text = tk.Text(
            self._log_frame,
            bg=c['log_bg'], fg=c['log_fg'],
            font=("Consolas", 9),
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            insertbackground=c['log_fg'],
            borderwidth=0,
            padx=8, pady=8,
        )
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._log_text.yview)

        # --- bottom bar ---
        self._bottom_frame = tk.Frame(self._outer_frame, bg=c['bg'])
        self._bottom_frame.grid(row=2, column=0, sticky='ew', pady=(10, 0))

        self._dark_btn = tk.Button(
            self._bottom_frame, text="Light Mode",
            bg=c['btn_bg'], fg=c['btn_fg'],
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            activebackground=c['accent_dark'],
            activeforeground=c['btn_fg'],
            cursor='hand2',
            padx=16, pady=4,
            borderwidth=0,
            command=self._on_toggle_dark,
        )
        self._dark_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._toggle_btn = tk.Button(
            self._bottom_frame, text="Show Logs",
            bg=c['btn_bg'], fg=c['btn_fg'],
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            activebackground=c['accent_dark'],
            activeforeground=c['btn_fg'],
            cursor='hand2',
            padx=16, pady=4,
            borderwidth=0,
            command=self._on_toggle_logs,
        )
        self._toggle_btn.pack(side=tk.LEFT)

        self._clear_btn = tk.Button(
            self._bottom_frame, text="Clear",
            bg=c['btn_bg'], fg=c['btn_fg'],
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            activebackground=c['accent_dark'],
            activeforeground=c['btn_fg'],
            cursor='hand2',
            padx=12, pady=4,
            borderwidth=0,
            command=self._on_clear_log,
        )

        self._copy_btn = tk.Button(
            self._bottom_frame, text="Copy",
            bg=c['btn_bg'], fg=c['btn_fg'],
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            activebackground=c['accent_dark'],
            activeforeground=c['btn_fg'],
            cursor='hand2',
            padx=12, pady=4,
            borderwidth=0,
            command=self._on_copy_log,
        )

        self._root.update_idletasks()
        w = self._root.winfo_reqwidth()
        h = self._root.winfo_reqheight()
        self._root.minsize(w, h)
        self._log_hidden_width = w
        self._log_hidden_height = h

        # center on screen
        ws = self._root.winfo_screenwidth()
        hs = self._root.winfo_screenheight()
        self._root.geometry(f"+{(ws-w)//2}+{(hs-h)//2}")

        self._poll_logs()
        self._ready.set()

    def _poll_logs(self):
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
            self._content_frame.columnconfigure(0, weight=0)
            self._content_frame.columnconfigure(1, weight=1)
            self._qr_frame.grid(row=0, column=0, sticky='nw', padx=(0, 15))
            self._log_frame.grid(row=0, column=1, sticky='nsew')
            self._log_pos = 0
            self._clear_btn.pack(side=tk.LEFT, padx=(8, 0))
            self._copy_btn.pack(side=tk.LEFT, padx=(4, 0))
            self._root.update_idletasks()
            self._root.minsize(1275, 420)
            self._root.geometry("1275x420")
        else:
            self._qr_frame.grid(row=0, column=0, sticky='')
            self._content_frame.columnconfigure(0, weight=1)
            self._content_frame.columnconfigure(1, weight=0)
            self._log_frame.grid_forget()
            self._clear_btn.pack_forget()
            self._copy_btn.pack_forget()
            self._root.update_idletasks()
            self._root.minsize(
                self._log_hidden_width, self._log_hidden_height
            )
            self._root.geometry(
                f"{self._log_hidden_width}x{self._log_hidden_height}"
            )

    def _on_close(self):
        self.hide()

    def _run(self):
        import traceback
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
            import logging
            logging.getLogger("pcremote").error(
                "Dashboard crashed: %s", traceback.format_exc()
            )

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
            state["dashboard"] = DashboardWindow(
                url,
                server_running=state["running"],
                on_toggle_server=lambda: do_stop(icon, item) if state["running"] else do_start(icon, item),
            )
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
