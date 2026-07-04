import os
import subprocess
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
            qr = qrcode.QRCode(border=2)
            qr.add_data(data)
            qr.make(fit=True)
            matrix = qr.modules
            lines = []
            for row in range(len(matrix)):
                line_parts = []
                for col in range(len(matrix[row])):
                    line_parts.append("  " if matrix[row][col] else "\033[47m  \033[0m")
                lines.append("".join(line_parts))
            return "\n".join(lines)
        except Exception:
            return None

    def display(self, data: str) -> bool:
        if os.name == 'nt':
            if self._display_gui(data):
                return True
        result = self.generate(data)
        if result:
            print()
            print(result)
            print()
            return True
        if os.name != 'nt':
            return self._try_qrencode_fallback(data)
        return False

    def _display_gui(self, data: str) -> bool:
        try:
            import tkinter as tk
            import qrcode as qrlib
        except ImportError:
            return False

        try:
            root = tk.Tk()
            root.title("PcRemote - Scan to Connect")
            root.configure(bg='white')
            root.resizable(False, False)

            qr = qrlib.QRCode(box_size=8, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img = img.resize((300, 300))
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(img)
            label = tk.Label(root, image=photo, bg='white')
            label.image = photo
            label.pack(padx=20, pady=(20, 5))

            url_label = tk.Label(
                root, text=data, bg='white', fg='#555',
                font=("Consolas", 9)
            )
            url_label.pack(pady=(0, 20))

            ws = root.winfo_screenwidth()
            hs = root.winfo_screenheight()
            root.geometry(f"+{ws//2-170}+{hs//2-200}")
            root.lift()
            root.attributes('-topmost', True)
            root.after(100, lambda: root.attributes('-topmost', False))
            root.after(15000, root.destroy)
            root.mainloop()
            return True
        except Exception:
            return False

    def _try_qrencode_fallback(self, data: str) -> bool:
        try:
            r = subprocess.run(
                ["qrencode", "-t", "UTF8", data],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and r.stdout.strip():
                print()
                for line in r.stdout.strip().split("\n"):
                    print(f"  {line}")
                print()
                return True
        except Exception:
            pass
        return False


class FallbackQrBackend(QrBackend):
    def generate(self, data: str) -> Optional[str]:
        return None

    def display(self, data: str):
        print()
        print(f"  QR code not available. Connect to: {data}")
        print()
