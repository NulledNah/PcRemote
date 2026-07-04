import json
import os
import secrets


def _config_dir() -> str:
    if os.name == 'nt':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        path = os.path.join(base, 'PcRemote')
    else:
        xdg = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        path = os.path.join(xdg, 'pcremote')
    os.makedirs(path, exist_ok=True)
    return path


def _config_path() -> str:
    return os.path.join(_config_dir(), 'config.json')


def load_config() -> dict:
    path = _config_path()
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: dict):
    path = _config_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def get_or_create_token(config: dict = None) -> str:
    if config is None:
        config = load_config()
    token = config.get('auth_token')
    if not token:
        token = secrets.token_hex(16)
        config['auth_token'] = token
        save_config(config)
    return token


def get_setting(key: str, default=None):
    config = load_config()
    return config.get(key, default)


def set_setting(key: str, value):
    config = load_config()
    config[key] = value
    save_config(config)


def get_data_dir() -> str:
    return _config_dir()
