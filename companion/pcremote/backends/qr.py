import os
import subprocess
import tempfile
from typing import Optional

from .base import QrBackend


class QrBackends:
    @staticmethod
    def create() -> QrBackend:
        backend = PythonQrcodeBackend()
        if backend.available():
            return backend
        return FallbackQrBackend()


class PythonQrcodeBackend(QrBackend):
    def available(self) -> bool:
        try:
            import qrcode  # noqa: F401
            return True
        except ImportError:
            return False

    def generate(self, data: str) -> Optional[str]:
        try:
            import qrcode
            qr = qrcode.QRCode(border=1)
            qr.add_data(data)
            qr.make(fit=True)
            modules = qr.modules
            size = len(modules)
            lines = []
            for row in range(0, size, 2):
                parts = []
                for col in range(size):
                    top = modules[row][col]
                    bottom = modules[row + 1][col] if row + 1 < size else False
                    if top and bottom:
                        parts.append('\u2588')
                    elif top:
                        parts.append('\u2580')
                    elif bottom:
                        parts.append('\u2584')
                    else:
                        parts.append(' ')
                lines.append(''.join(parts))
            return '\n'.join(lines)
        except Exception:
            return None

    def display(self, data: str) -> bool:
        if self._display_image(data):
            return True
        result = self.generate(data)
        if result:
            print()
            print(result)
            print()
            return True
        return False

    def _display_image(self, data: str) -> bool:
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
        except Exception:
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

    def display(self, data: str):
        print()
        print(f"  QR code not available. Connect to: {data}")
        print()
