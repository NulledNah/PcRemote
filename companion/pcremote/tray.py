import ctypes
import os
import sys
from datetime import datetime


_CONSOLE_ALLOCATED = False


def _ctrl_handler(ctrl_type):
    if ctrl_type == 2:
        _detach_console()
        return True
    return False


def _detach_console():
    global _CONSOLE_ALLOCATED
    if not _CONSOLE_ALLOCATED:
        return
    try:
        kernel32 = ctypes.windll.kernel32
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        import logging
        logger = logging.getLogger("pcremote")
        for h in list(logger.handlers):
            if isinstance(h, logging.StreamHandler):
                logger.removeHandler(h)
        kernel32.FreeConsole()
        _CONSOLE_ALLOCATED = False
    except Exception:
        pass


def show_console():
    global _CONSOLE_ALLOCATED
    if os.name != 'nt':
        return

    if _CONSOLE_ALLOCATED:
        _detach_console()

    try:
        kernel32 = ctypes.windll.kernel32
        if not kernel32.AllocConsole():
            return
        _CONSOLE_ALLOCATED = True

        kernel32.SetConsoleTitleW("PcRemote Server")
        kernel32.SetConsoleCtrlHandler(
            ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)(_ctrl_handler), True
        )

        sys.stdout = open('CONOUT$', 'w', buffering=1)
        sys.stderr = open('CONOUT$', 'w', buffering=1)

        import logging
        from .config import get_data_dir
        logger = logging.getLogger("pcremote")
        for h in list(logger.handlers):
            if isinstance(h, logging.StreamHandler):
                logger.removeHandler(h)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-7s  %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)

        log_file = os.path.join(get_data_dir(),
                                f"pcremote-{datetime.now():%Y%m%d}.log")
        if os.path.isfile(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    sys.stdout.write(f.read())
                    sys.stdout.flush()
            except Exception:
                pass

        logger.info("--- Console attached, live log streaming ---")
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


def run_tray(on_stop_server, on_start_server, on_quit,
             on_show_console=None, on_init=None, on_show_qr=None):
    if os.name != 'nt':
        return False

    try:
        from pystray import Icon as TrayIcon, Menu, MenuItem
    except ImportError:
        return False

    image = _load_image()
    state = {"running": True, "console_shown": False}
    on_show_console = on_show_console or (lambda: None)
    on_show_qr = on_show_qr or (lambda: None)

    def do_qr(icon, item):
        on_show_qr()

    def do_console(icon, item):
        if not state["console_shown"]:
            state["console_shown"] = True
            on_show_console()
            icon.menu = _build_menu(state, do_qr, do_console, do_stop, do_start, do_quit)
            icon.update_menu()

    def do_stop(icon, item):
        if state["running"]:
            on_stop_server()
            state["running"] = False
            icon.menu = _build_menu(state, do_qr, do_console, do_stop, do_start, do_quit)
            icon.update_menu()

    def do_start(icon, item):
        if not state["running"]:
            on_start_server()
            state["running"] = True
            icon.menu = _build_menu(state, do_qr, do_console, do_stop, do_start, do_quit)
            icon.update_menu()

    def do_quit(icon, item):
        global _CONSOLE_ALLOCATED
        if state["running"]:
            on_stop_server()
            state["running"] = False
        icon.stop()
        if _CONSOLE_ALLOCATED:
            _detach_console()
        on_quit()

    def setup(icon):
        icon.visible = True
        if on_init:
            on_init()

    menu = _build_menu(state, do_qr, do_console, do_stop, do_start, do_quit)
    icon = TrayIcon("PcRemote", image, menu=menu)
    icon.run(setup)
    return True


def _build_menu(state, do_qr, do_console, do_stop, do_start, do_quit):
    from pystray import Menu, MenuItem
    items = []
    items.append(MenuItem("Show QR Code", do_qr))
    if state["console_shown"]:
        items.append(MenuItem("Console (visible)", None, enabled=False))
    else:
        items.append(MenuItem("Show Console", do_console))
    items.append(Menu.SEPARATOR)
    if state["running"]:
        items.append(MenuItem("Stop Server", do_stop))
    else:
        items.append(MenuItem("Start Server", do_start))
    items.append(Menu.SEPARATOR)
    items.append(MenuItem("Quit", do_quit))
    return Menu(*items)
