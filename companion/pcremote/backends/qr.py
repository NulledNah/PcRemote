import os
import subprocess
import tempfile
import threading
from typing import Optional

from .base import QrBackend


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


class QrBackends:
    @staticmethod
    def create() -> QrBackend:
        backend = PythonQrcodeBackend()
        if backend.available():
            return backend
        return FallbackQrBackend()


class PythonQrcodeBackend(QrBackend):
    def __init__(self):
        self._qr_window = None
        self._qr_close_flag = None

    def available(self) -> bool:
        try:
            import qrcode  # noqa: F401
            return True
        except ImportError:
            return False

    def close_qr(self):
        if self._qr_close_flag:
            self._qr_close_flag.set()

    def generate(self, data: str) -> Optional[str]:
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
            return '\n'.join(lines)
        except Exception:
            return None

    def display(self, data: str) -> bool:
        self.close_qr()
        if os.name == 'nt':
            if self._display_tkinter(data):
                return True
            result = self.generate(data)
            if result:
                print()
                print(result)
                print()
                return True
            if self._display_file(data):
                return True
            return False
        else:
            result = self.generate(data)
            if result:
                print()
                print(result)
                print()
                return True
            if self._display_file(data):
                return True
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

    def _display_file(self, data: str) -> bool:
        path = None
        try:
            import qrcode
            from PIL import Image
            qr = qrcode.QRCode(box_size=12, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            w, h = img.size
            img = img.resize((w * 2, h * 2), Image.NEAREST)
            fd, path = tempfile.mkstemp(suffix='.png', prefix='pcremote_qr_')
            os.close(fd)
            img.save(path, format='PNG')
        except Exception as e:
            import logging
            logging.getLogger("pcremote").debug("QR file generation failed: %s", e)
            return False

        opened = False
        try:
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            opened = True
        except Exception:
            pass

        print()
        if opened:
            print(f"  QR image opened. Connect to: {data}")
        else:
            print(f"  QR saved to: {path}")
            print(f"  Connect to: {data}")
        return True


class FallbackQrBackend(QrBackend):
    def generate(self, data: str) -> Optional[str]:
        return None

    def close_qr(self):
        pass

    def display(self, data: str):
        print()
        print(f"  QR code not available. Connect to: {data}")
        print()
