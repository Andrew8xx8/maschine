"""
Maschine Mikro MK3 Python Driver
==================================

Unified Python driver for Native Instruments Maschine Mikro MK3.

Usage:
    >>> from maschine import MaschineDevice, find_devices, Color
    >>>
    >>> # Find and connect devices
    >>> devices = find_devices(max_count=4)
    >>>
    >>> # Control LEDs
    >>> devices[0].set_pad_light(0, Color.RED)
    >>> devices[0].set_all_pads(Color.BLUE)
    >>> devices[0].clear()
    >>>
    >>> # Read pad events
    >>> pressed = devices[0].read_pads(timeout_ms=10)
    >>>
    >>> # Cleanup
    >>> for device in devices:
    >>>     device.close()

Features:
    - Multi-device support (up to 4 controllers)
    - Full LED control with 17-color palette
    - Pad event detection with velocity
    - Thread-safe operations
    - Proper error handling and logging
"""

from .device import MaschineDevice, find_devices, close_all_devices, setup_devices_with_config
from .constants import (
    Color,
    PadEventType,
    BRIGHTNESS_OFF,
    BRIGHTNESS_DIM,
    BRIGHTNESS_NORMAL,
    BRIGHTNESS_BRIGHT,
    PAD_COUNT,
    MAX_DEVICES,
)
from .device_config import (
    load_device_config,
    save_device_config,
    sort_devices_by_config,
    get_config_path,
    has_config,
)
from .screen import Screen

__version__ = "1.0.0"
__author__ = "Maschine MK3 Project"

__all__ = [
    # Main classes
    "MaschineDevice",
    "find_devices",
    "close_all_devices",
    "setup_devices_with_config",
    "Screen",

    # Color palette
    "Color",

    # Event types
    "PadEventType",

    # Brightness levels
    "BRIGHTNESS_OFF",
    "BRIGHTNESS_DIM",
    "BRIGHTNESS_NORMAL",
    "BRIGHTNESS_BRIGHT",

    # Constants
    "PAD_COUNT",
    "MAX_DEVICES",

    # Device configuration
    "load_device_config",
    "save_device_config",
    "sort_devices_by_config",
    "get_config_path",
    "has_config",
]

