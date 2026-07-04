import os
import sys
import threading


def run_tray(server_start_fn, server_stop_fn):
    if os.name != 'nt':
        return False

    try:
        from pystray import Icon as TrayIcon, Menu, MenuItem
        from PIL import Image, ImageDraw
    except ImportError:
        return False

    def create_image():
        img = Image.new('RGB', (64, 64), color='#1a73e8')
        draw = ImageDraw.Draw(img)
        draw.rectangle([16, 20, 48, 44], fill='white')
        draw.polygon([(30, 44), (50, 32), (50, 56)], fill='white')
        return img

    def on_quit(icon, item):
        icon.stop()
        server_stop_fn()
        sys.exit(0)

    def setup(icon):
        icon.visible = True

    menu = Menu(
        MenuItem("Start Server", lambda icon, item: server_start_fn()),
        MenuItem("Stop Server", lambda icon, item: server_stop_fn()),
        MenuItem("Quit", on_quit),
    )

    icon = TrayIcon("PcRemote", create_image(), menu=menu)
    threading.Thread(target=icon.run, args=(setup,), daemon=True).start()
    return True
