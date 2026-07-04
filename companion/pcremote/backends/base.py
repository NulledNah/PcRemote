from abc import ABC, abstractmethod
from typing import Optional


class InputBackend(ABC):
    @abstractmethod
    def key(self, name: str, action: str):
        ...

    @abstractmethod
    def mouse_move(self, dx: float, dy: float):
        ...

    @abstractmethod
    def mouse_button(self, button: str, action: str):
        ...

    @abstractmethod
    def mouse_scroll(self, dx: float, dy: float):
        ...

    @abstractmethod
    def type_text(self, text: str):
        ...

    @abstractmethod
    def close(self):
        ...


class VolumeBackend(ABC):
    @property
    @abstractmethod
    def supports_precise_volume(self) -> bool:
        ...

    @abstractmethod
    def get_volume(self) -> dict:
        ...

    @abstractmethod
    def set_volume(self, vol: int):
        ...

    @abstractmethod
    def toggle_mute(self) -> bool:
        ...


class QrBackend(ABC):
    @abstractmethod
    def generate(self, data: str) -> Optional[str]:
        """Returns QR as string for terminal, or None if unavailable."""

    @abstractmethod
    def display(self, data: str):
        """Display QR code to the user (terminal, GUI window, etc.)."""
