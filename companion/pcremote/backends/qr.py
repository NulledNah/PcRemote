import os
import threading


def _find_icon_path():
    candidates = []
    try:
        import sys as _sys
        base = getattr(_sys, '_MEIPASS', '')
        if base:
            candidates.append(os.path.join(base, 'icon.ico'))
    except Exception:
        pass
    candidates.append(os.path.join(os.path.dirname(__file__), '..', '..', 'icon.ico'))
    candidates.append(os.path.join(os.path.dirname(__file__), '..', 'icon.ico'))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _set_window_icon(root):
    icon_path = _find_icon_path()
    if icon_path:
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass


class QrCodeDisplay:
    def __init__(self):
        self._qr_window = None
        self._qr_close_flag = None

    def close_qr(self):
        if self._qr_close_flag:
            self._qr_close_flag.set()

    def display(self, data: str) -> bool:
        self.close_qr()
        if os.name == 'nt':
            if self._display_tkinter(data):
                return True
        return self._display_terminal(data)

    def _display_terminal(self, data: str) -> bool:
        try:
            import qrcode
            qr = qrcode.QRCode(box_size=1, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            modules = qr.modules
            size = len(modules)
            lines = []
            for row in range(size):
                parts = []
                for col in range(size):
                    if modules[row][col]:
                        parts.append('\u2588\u2588')
                    else:
                        parts.append('  ')
                lines.append(''.join(parts))
            print()
            print('\n'.join(lines))
            print()
            return True
        except Exception:
            return False

    def _display_tkinter(self, data: str) -> bool:
        try:
            import tkinter as tk
            import qrcode
            from PIL import Image, ImageTk
        except ImportError:
            return False

        try:
            qr = qrcode.QRCode(box_size=8, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img = img.resize((320, 320), Image.NEAREST)
        except Exception as e:
            import logging
            logging.getLogger("pcremote").debug("QR tkinter generation failed: %s", e)
            return False

        self._qr_close_flag = threading.Event()

        def _run():
            root = tk.Tk()
            root.title("PcRemote - Scan to Connect")
            root.configure(bg='white')
            root.resizable(False, False)

            _set_window_icon(root)

            photo = ImageTk.PhotoImage(img)
            label = tk.Label(root, image=photo, bg='white')
            label.image = photo
            label.pack(padx=20, pady=(20, 5))

            url_label = tk.Label(
                root, text=data, bg='white', fg='#555',
                font=("Consolas", 9),
            )
            url_label.pack(pady=(0, 20))

            root.update_idletasks()
            ws = root.winfo_screenwidth()
            hs = root.winfo_screenheight()
            w = root.winfo_width()
            h = root.winfo_height()
            root.geometry(f"+{ws//2 - w//2}+{hs//2 - h//2}")
            root.lift()
            root.attributes('-topmost', True)
            root.after(200, lambda: root.attributes('-topmost', False))

            def _check_close():
                if self._qr_close_flag.is_set():
                    root.destroy()
                    self._qr_window = None
                    return
                self._qr_window = root
                root.after(200, _check_close)

            root.after(200, _check_close)
            root.mainloop()
            self._qr_window = None

        threading.Thread(target=_run, daemon=True).start()
        return True
