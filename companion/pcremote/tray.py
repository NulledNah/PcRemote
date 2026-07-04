import ctypes
from ctypes import wintypes
import os
import sys
import threading
import time
from datetime import datetime


WM_USER = 0x0400
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_TRAYICON = WM_USER + 1
NIM_ADD = 0
NIM_DELETE = 2
NIM_MODIFY = 1
NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4
NIF_INFO = 0x10
NIIF_INFO = 1

NOTIFYICONDATAW_SIZE = ctypes.sizeof(wintypes.DWORD) * 2 + ctypes.sizeof(wintypes.HWND) + ctypes.sizeof(wintypes.UINT) * 2 + ctypes.sizeof(wintypes.WCHAR) * 128 + ctypes.sizeof(wintypes.DWORD) + ctypes.sizeof(wintypes.WCHAR) * 256 + ctypes.sizeof(wintypes.DWORD)


class _NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
    ]


user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32


class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt_x", wintypes.LONG),
        ("pt_y", wintypes.LONG),
    ]


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


def _load_hicon():
    path = _find_icon_path()
    if path:
        hicon = user32.LoadImageW(None, path, 1, 0, 0, 0x00000010 | 0x00000040)
        if hicon:
            return hicon
    return user32.LoadIconW(0, 32512)


def _get_log_path():
    from .config import get_data_dir
    return os.path.join(get_data_dir(),
                        f"pcremote-{datetime.now():%Y%m%d}.log")


class NativeTrayIcon:
    def __init__(self, on_left_click=None, on_right_click=None):
        self._on_left = on_left_click
        self._on_right = on_right_click
        self._hicon = _load_hicon()
        self._hwnd = None
        self._running = False

    def start(self):
        cls_name = f"PcRemoteTray_{id(self)}"
        wndproc = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)(self._wndproc)

        wc = _WNDCLASSW()
        wc.lpfnWndProc = wndproc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = cls_name
        user32.RegisterClassW(ctypes.byref(wc))

        self._hwnd = user32.CreateWindowExW(0, cls_name, "PcRemote", 0, 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)

        self._add_icon()
        self._running = True
        self._message_loop()

    def stop(self):
        self._running = False
        if self._hwnd:
            self._remove_icon()
            user32.DestroyWindow(self._hwnd)
            self._hwnd = None

    def _add_icon(self):
        nid = _NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(_NOTIFYICONDATA)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = self._hicon
        nid.szTip = "PcRemote Server"
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

    def _remove_icon(self):
        nid = _NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(_NOTIFYICONDATA)
        nid.hWnd = self._hwnd
        nid.uID = 1
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            if lparam == WM_LBUTTONUP and self._on_left:
                self._on_left()
            elif lparam == WM_RBUTTONUP and self._on_right:
                self._on_right()
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _message_loop(self):
        msg = _MSG()
        while self._running:
            while user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.05)


class DashboardWindow:
    def __init__(self, connection_url: str):
        self._url = connection_url
        self._root = None
        self._ready = threading.Event()
        self._show_flag = threading.Event()
        self._close_flag = threading.Event()
        self._logs_visible = False
        self._log_text = None
        self._log_pos = 0
        self._thread = None
        self._switch_btn = None

    def _create(self):
        import tkinter as tk
        import qrcode
        from PIL import Image, ImageTk

        BG = '#ffffff'
        FG = '#1a73e8'
        FG_DARK = '#1557b0'
        LOG_BG = '#0f172a'
        LOG_FG = '#e2e8f0'

        self._root = tk.Tk()
        self._root.title("PcRemote Dashboard")
        self._root.configure(bg=BG)
        self._root.resizable(False, False)
        self._root.withdraw()

        icon_path = _find_icon_path()
        if icon_path:
            try:
                self._root.iconbitmap(icon_path)
            except Exception:
                pass

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        main_frame = tk.Frame(self._root, bg=BG)
        main_frame.pack(padx=15, pady=15)

        left_frame = tk.Frame(main_frame, bg=BG)
        left_frame.pack(side=tk.LEFT)

        qr = qrcode.QRCode(box_size=6, border=3)
        qr.add_data(self._url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=FG_DARK, back_color=BG)
        img = img.resize((220, 220), Image.NEAREST)
        photo = ImageTk.PhotoImage(img)

        qr_label = tk.Label(left_frame, image=photo, bg=BG)
        qr_label.image = photo
        qr_label.pack()

        url_label = tk.Label(
            left_frame, text=self._url, bg=BG, fg='#666',
            font=("Consolas", 8)
        )
        url_label.pack(pady=(5, 0))

        self._log_frame = tk.Frame(main_frame, bg=BG)

        scrollbar = tk.Scrollbar(self._log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._log_text = tk.Text(
            self._log_frame, height=22, width=52,
            bg=LOG_BG, fg=LOG_FG,
            font=("Consolas", 8),
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            insertbackground=LOG_FG,
            borderwidth=0,
            padx=8, pady=8,
        )
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._log_text.yview)

        bottom_frame = tk.Frame(self._root, bg=BG)
        bottom_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        self._switch_var = tk.BooleanVar(value=False)

        switch_canvas = tk.Canvas(
            bottom_frame, width=44, height=24,
            bg=BG, highlightthickness=0
        )
        switch_canvas.pack(side=tk.LEFT)

        self._switch_btn = switch_canvas
        self._switch_canvas = switch_canvas

        def _draw_switch(on=False):
            switch_canvas.delete("all")
            if on:
                _rounded_rect(switch_canvas, 0, 0, 44, 24, 12, fill=FG)
                switch_canvas.create_oval(22, 2, 42, 22, fill='white', outline='')
            else:
                _rounded_rect(switch_canvas, 0, 0, 44, 24, 12, fill='#ccc')
                switch_canvas.create_oval(2, 2, 22, 22, fill='white', outline='')

        _draw_switch(False)

        switch_label = tk.Label(
            bottom_frame, text="  Show Logs", bg=BG, fg='#333',
            font=("Segoe UI", 9)
        )
        switch_label.pack(side=tk.LEFT)

        def _on_switch_click(event):
            current = self._switch_var.get()
            self._switch_var.set(not current)
            self._logs_visible = not current
            _draw_switch(self._logs_visible)
            self._update_log_visibility()

        switch_canvas.bind("<Button-1>", _on_switch_click)

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
        import tkinter as tk
        if self._logs_visible:
            self._log_frame.pack(side=tk.LEFT, padx=(15, 0))
            self._log_pos = 0
        else:
            self._log_frame.pack_forget()

    def _on_close(self):
        self.hide()

    def _run(self):
        import tkinter as tk
        try:
            self._create()
            while not self._close_flag.is_set():
                try:
                    if self._show_flag.wait(timeout=0.1):
                        self._show_flag.clear()
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
        self._show_flag.set()

    def hide(self):
        self._show_flag.clear()
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


def _create_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """Helper to create rounded rectangle on tkinter canvas."""
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def _show_popup_menu(menu_items):
    import tkinter as tk
    popup = tk.Menu(None, tearoff=0, bg='white', fg='#333',
                    activebackground='#1a73e8', activeforeground='white',
                    font=("Segoe UI", 9))
    for label, callback, enabled in menu_items:
        if label == '-':
            popup.add_separator()
        else:
            state = tk.NORMAL if enabled else tk.DISABLED
            popup.add_command(label=label, command=callback, state=state)
    popup.tk_popup(*popup.winfo_pointerxy())
    popup.grab_release()


def run_tray(on_stop_server, on_start_server, on_quit,
             on_init=None, get_connection_url=None):
    if os.name != 'nt':
        return False

    get_connection_url = get_connection_url or (lambda: "")
    state = {"running": True, "dashboard": None}

    def do_dashboard():
        if state["dashboard"] is None:
            url = get_connection_url()
            state["dashboard"] = DashboardWindow(url)
        state["dashboard"].show()

    def do_stop():
        if state["running"]:
            on_stop_server()
            state["running"] = False

    def do_start():
        if not state["running"]:
            on_start_server()
            state["running"] = True

    def do_quit():
        if state["running"]:
            on_stop_server()
            state["running"] = False
        if state["dashboard"]:
            state["dashboard"].close()
        tray.stop()
        on_quit()

    def _build_menu():
        items = [
            ("Show Dashboard", do_dashboard, True),
            ("-", None, True),
        ]
        if state["running"]:
            items.append(("Stop Server", do_stop, True))
        else:
            items.append(("Start Server", do_start, True))
        items.append(("-", None, True))
        items.append(("Quit", do_quit, True))
        return items

    def on_right_click():
        t = threading.Thread(target=lambda: _show_popup_menu(_build_menu()), daemon=True)
        t.start()

    tray = NativeTrayIcon(
        on_left_click=do_dashboard,
        on_right_click=on_right_click,
    )

    if on_init:
        threading.Timer(0.5, on_init).start()

    tray.start()
    return True
