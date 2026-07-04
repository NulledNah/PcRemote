import ctypes
import os
import sys


def show_console():
    if os.name != 'nt':
        return
    try:
        kernel32 = ctypes.windll.kernel32
        if kernel32.AllocConsole():
            kernel32.SetConsoleTitleW("PcRemote Server")
            sys.stdout = open('CONOUT$', 'w', buffering=1)
            sys.stderr = open('CONOUT$', 'w', buffering=1)
            import logging
            logger = logging.getLogger("pcremote")
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s  %(levelname)-7s  %(message)s",
                datefmt="%H:%M:%S",
            ))
            logger.addHandler(handler)
            logger.info("Console attached - live log streaming")
    except Exception:
        pass


def _load_image():
    candidates = []
    try:
        import sys as _sys
        base = getattr(_sys, '_MEIPASS', '')
        if base:
            candidates.append(os.path.join(base, 'icon.ico'))
    except Exception:
        pass
    candidates.append(os.path.join(os.path.dirname(__file__), '..', 'icon.ico'))
    candidates.append(os.path.join(os.path.dirname(sys.executable), 'icon.ico'))

    for icon_path in candidates:
        if os.path.isfile(icon_path):
            try:
                from PIL import Image
                return Image.open(icon_path)
            except Exception:
                continue

    from PIL import Image, ImageDraw
    img = Image.new('RGB', (64, 64), color='#1a73e8')
    draw = ImageDraw.Draw(img)
    draw.rectangle([16, 20, 48, 44], fill='white')
    draw.polygon([(30, 44), (50, 32), (50, 56)], fill='white')
    return img


def run_tray(on_stop_server, on_start_server, on_quit, on_show_console=None):
    if os.name != 'nt':
        return False

    try:
        from pystray import Icon as TrayIcon, Menu, MenuItem
    except ImportError:
        return False

    image = _load_image()
    state = {"running": True, "console_shown": False}
    on_show_console = on_show_console or (lambda: None)

    def do_console(icon, item):
        if not state["console_shown"]:
            state["console_shown"] = True
            on_show_console()
            icon.menu = _build_menu(state, do_console, do_stop, do_start, do_quit)
            icon.update_menu()

    def do_stop(icon, item):
        if state["running"]:
            on_stop_server()
            state["running"] = False
            icon.menu = _build_menu(state, do_console, do_stop, do_start, do_quit)
            icon.update_menu()

    def do_start(icon, item):
        if not state["running"]:
            on_start_server()
            state["running"] = True
            icon.menu = _build_menu(state, do_console, do_stop, do_start, do_quit)
            icon.update_menu()

    def do_quit(icon, item):
        if state["running"]:
            on_stop_server()
            state["running"] = False
        icon.stop()
        on_quit()

    menu = _build_menu(state, do_console, do_stop, do_start, do_quit)
    icon = TrayIcon("PcRemote", image, menu=menu)
    icon.run(setup=lambda i: setattr(i, 'visible', True))
    return True


def _build_menu(state, do_console, do_stop, do_start, do_quit):
    from pystray import Menu, MenuItem
    items = []
    if state["console_shown"]:
        items.append(MenuItem("Console (visible)", None, enabled=False))
    else:
        items.append(MenuItem("Show Console", do_console))
    items.append(MenuItem.SEPARATOR)
    if state["running"]:
        items.append(MenuItem("Stop Server", do_stop))
    else:
        items.append(MenuItem("Start Server", do_start))
    items.append(MenuItem.SEPARATOR)
    items.append(MenuItem("Quit", do_quit))
    return Menu(*items)
