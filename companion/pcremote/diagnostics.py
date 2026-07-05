import os
import socket
import subprocess
import sys
import tempfile
import time
from typing import Optional

from .logsetup import get as get_logger


def run_diagnostics(port: int, logger=None) -> dict:
    if logger is None:
        logger = get_logger()

    results = {
        "python": False,
        "firewall": None,
        "port_available": False,
        "input_backend": False,
        "volume_backend": "unknown",
        "warnings": [],
    }

    results["python"] = True
    logger.info("  [OK] Python %s detected", sys.version.split()[0])

    if os.name == 'nt':
        _check_windows(results, port, logger)
    else:
        _check_linux(results, port, logger)

    return results


def _check_linux(results: dict, port: int, logger):
    if _port_available(port):
        results["port_available"] = True
        logger.info("  [OK] Port %d available", port)
    else:
        logger.warning("  [WARN] Port %d in use", port)

    try:
        r = subprocess.run(
            ["lsmod"], capture_output=True, text=True, timeout=3
        )
        if "uinput" in r.stdout:
            results["input_backend"] = True
            logger.info("  [OK] uinput kernel module loaded")
        else:
            results["warnings"].append(
                "uinput not loaded. Run: sudo modprobe uinput"
            )
            logger.warning("  [WARN] uinput not loaded")
    except Exception:
        pass

    check_user_group_linux(logger)

    try:
        r = subprocess.run(
            ["pactl", "info"], capture_output=True, text=True, timeout=3
        )
        if r.returncode == 0:
            results["volume_backend"] = "pactl"
            logger.info("  [OK] PulseAudio (pactl) available")
        else:
            results["warnings"].append("pactl not available - volume control disabled")
            logger.warning("  [WARN] pactl not available")
    except FileNotFoundError:
        results["warnings"].append("pactl not found - volume control disabled")
        logger.warning("  [WARN] pactl not found")


def _check_windows(results: dict, port: int, logger):
    if _port_available(port):
        results["port_available"] = True
        logger.info("  [OK] Port %d available", port)
    else:
        logger.warning("  [WARN] Port %d in use", port)

    results["input_backend"] = True
    logger.info("  [OK] Windows SendInput backend available")

    try:
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        if devices is not None and devices.EndpointVolume is not None:
            results["volume_backend"] = "core_audio"
            logger.info("  [OK] Volume control via Windows Core Audio API")
        else:
            results["volume_backend"] = "media_keys"
            logger.info("  [OK] Volume control via media keys (no audio device)")
    except ImportError:
        results["volume_backend"] = "media_keys"
        logger.info("  [OK] Volume control via media keys (pycaw not installed)")
    except Exception:
        results["volume_backend"] = "media_keys"
        logger.info("  [OK] Volume control via media keys (audio init failed)")

    if not _firewall_port_open(port):
        logger.warning("  [WARN] Windows Firewall may block port %d", port)
        results["firewall"] = "blocked"
        results["warnings"].append(
            f"Firewall may block port {port}. Run as admin or add rule manually."
        )
    else:
        results["firewall"] = "open"
        logger.info("  [OK] Firewall allows port %d", port)

    if _is_admin():
        logger.warning(
            "  [WARN] Running as admin - SendInput may not work in some contexts. "
            "Run as normal user."
        )
        results["warnings"].append(
            "Running as administrator may prevent input simulation."
        )


def _port_available(port: int) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.bind(("0.0.0.0", port))
        s.close()
        return True
    except OSError:
        return False


def _firewall_port_open(port: int) -> bool:
    try:
        result = subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "show", "rule",
                "name=PcRemote WebSocket Server",
            ],
            capture_output=True, text=True, timeout=5,
            check=False,
        )
        return "PcRemote WebSocket Server" in result.stdout
    except Exception:
        return False


def _is_admin() -> bool:
    if os.name != 'nt':
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def auto_fix_firewall(port: int, logger=None) -> bool:
    if os.name != 'nt':
        return True

    if logger is None:
        logger = get_logger()

    rule_name = "PcRemote WebSocket Server"

    if _is_admin():
        return _add_firewall_rule(rule_name, port, logger)

    bat_path = os.path.join(tempfile.gettempdir(), "pcremote_firewall.bat")
    try:
        with open(bat_path, 'w', encoding='ascii') as f:
            f.write('@echo off\r\n')
            f.write(f'echo Adding PcRemote firewall rule for port {port}...\r\n')
            f.write(f'netsh advfirewall firewall delete rule name="{rule_name}" >nul 2>&1\r\n')
            f.write(f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=allow protocol=TCP localport={port} profile=any\r\n')
            f.write(f'if %errorlevel% equ 0 (\r\n')
            f.write(f'    echo Firewall rule added successfully.\r\n')
            f.write(f') else (\r\n')
            f.write(f'    echo Failed to add firewall rule. You may need to run as Administrator.\r\n')
            f.write(f'    pause\r\n')
            f.write(f')\r\n')

        logger.info("  Requesting admin privileges to add firewall rule (UAC prompt will appear)...")
        logger.info("  Please click YES on the User Account Control dialog.")

        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f'Start-Process "{bat_path}" -Verb RunAs -Wait'],
            capture_output=True, timeout=30,
            check=False,
        )

        for _ in range(5):
            time.sleep(1)
            if _firewall_port_open(port):
                logger.info("  [OK] Windows Firewall rule added for port %d (any profile)", port)
                return True

        logger.warning("  [WARN] Firewall rule could not be added. You may have declined the UAC prompt.")
    except Exception as e:
        logger.warning("  [WARN] Could not add firewall rule: %s", e)
    finally:
        try:
            os.remove(bat_path)
        except OSError:
            pass

    logger.warning(
        "  [WARN] Manually add the rule by running as admin:\n"
        f'    netsh advfirewall firewall add rule name="%s" dir=in action=allow protocol=TCP localport=%d profile=any',
        rule_name, port,
    )
    return False


def _add_firewall_rule(rule_name: str, port: int, logger) -> bool:
    try:
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"],
            capture_output=True, timeout=10, check=False,
        )
        result = subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule_name}",
                "dir=in",
                "action=allow",
                "protocol=TCP",
                f"localport={port}",
                "profile=any",
            ],
            capture_output=True, timeout=10,
            check=False,
        )
        if result.returncode == 0:
            logger.info("  [OK] Windows Firewall rule added for port %d (any profile)", port)
            return True
        else:
            logger.warning("  [WARN] Firewall rule add failed (code %d)", result.returncode)
            return False
    except Exception as e:
        logger.warning("  [WARN] Could not add firewall rule: %s", e)
        return False


def check_user_group_linux(logger=None) -> bool:
    if os.name == 'nt':
        return True
    if logger is None:
        logger = get_logger()
    try:
        import grp
        input_grp = grp.getgrnam("input")
        if os.geteuid() == 0 or os.getlogin() in input_grp.gr_mem:
            return True
    except Exception:
        pass
    logger.warning("  [WARN] User not in 'input' group. Run: sudo usermod -aG input $USER")
    return False


if os.name == 'nt':
    import ctypes
else:
    ctypes = None
