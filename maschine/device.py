"""
Unified MaschineDevice class
==============================

Единая реализация управления устройством Maschine Mikro MK3.
Все файлы проекта должны использовать этот класс вместо дублирования кода.
"""

import hid
import time
import os
import logging
from typing import Optional, List, Callable
from threading import Lock

from .constants import (
    VENDOR_ID,
    PRODUCT_ID,
    LED_REPORT_ID,
    LED_BUFFER_SIZE,
    PAD_LED_OFFSET,
    BRIGHTNESS_BRIGHT,
    Color,
    PadEventType,
    COLOR_INDEX_SHIFT,
    BRIGHTNESS_MASK,
    PAD_COUNT,
    HID_READ_SIZE,
    get_nhl_registration_msg,
    INIT_SEQUENCES,
    REGISTRATION_DELAY,
    INIT_DELAY_SHORT,
    INIT_DELAY_LONG,
)

logger = logging.getLogger(__name__)


class MaschineDevice:
    """
    Maschine Mikro MK3 Device Controller

    Manages connection, initialization, LED control, and event reading
    for a single Maschine Mikro MK3 device.

    Example:
        >>> devices = find_devices()
        >>> device = devices[0]
        >>> device.set_pad_light(0, Color.RED)
        >>> device.clear()
        >>> device.close()
    """

    def __init__(self, device_info: dict, debug: bool = False):
        """
        Initialize device controller

        Args:
            device_info: Device info dict from hid.enumerate()
            debug: Enable debug logging
        """
        self.info = device_info
        self.serial = device_info['serial_number']
        self.debug = debug
        self.device: Optional[hid.device] = None
        self.lock = Lock()

        # LED buffer: 81 bytes [Report ID][Buttons][Pads][Sliders]
        self.led_buffer = bytearray(LED_BUFFER_SIZE)
        self.led_buffer[0] = LED_REPORT_ID

    def connect(self) -> bool:
        """
        Connect and initialize device

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.device = hid.device()
            self.device.open_path(self.info['path'])

            if self.debug:
                manufacturer = self.device.get_manufacturer_string()
                product = self.device.get_product_string()
                logger.info(f"[{self.serial}] Connected: {manufacturer} {product}")

            # NHL Registration
            client_id = os.urandom(8)
            register_msg = get_nhl_registration_msg(client_id)
            self.device.write(register_msg)

            if self.debug:
                logger.info(f"[{self.serial}] NHL Registration: client_id={client_id.hex()}")

            time.sleep(REGISTRATION_DELAY)

            # Wake-up sequences
            if self.debug:
                logger.info(f"[{self.serial}] Sending {len(INIT_SEQUENCES)} init sequences...")

            for i, seq in enumerate(INIT_SEQUENCES, 1):
                self.device.write(seq)
                if self.debug:
                    header = ' '.join(f'{b:02x}' for b in seq[:8])
                    logger.debug(f"[{self.serial}]   Init #{i}: [{header}...]")
                time.sleep(INIT_DELAY_SHORT)

            self.device.set_nonblocking(True)
            time.sleep(INIT_DELAY_LONG)

            # Clear all LEDs
            self.clear()

            if self.debug:
                logger.info(f"[{self.serial}] ✅ Initialized successfully")

            return True

        except OSError as e:
            logger.error(f"[{self.serial}] Connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"[{self.serial}] Unexpected error during connection: {e}")
            return False

    def set_pad_light(
        self,
        pad_idx: int,
        color_idx: int,
        brightness: int = BRIGHTNESS_BRIGHT,
        on: bool = True
    ) -> None:
        """
        Set single pad light

        Args:
            pad_idx: Pad index (0-15)
            color_idx: Color palette index (use Color.RED, Color.BLUE, etc.)
            brightness: Brightness level (0x00-0x7f, default BRIGHTNESS_BRIGHT)
            on: Enable or disable light
        """
        if not (0 <= pad_idx < PAD_COUNT):
            logger.warning(f"[{self.serial}] Invalid pad index: {pad_idx}")
            return

        with self.lock:
            if on and color_idx > 0:
                value = (color_idx << COLOR_INDEX_SHIFT) | (brightness & BRIGHTNESS_MASK)
            else:
                value = 0

            self.led_buffer[PAD_LED_OFFSET + pad_idx] = value

            try:
                self.device.write(self.led_buffer)
            except OSError as e:
                logger.warning(f"[{self.serial}] Failed to write LED: {e}")
            except Exception as e:
                logger.error(f"[{self.serial}] Unexpected error in set_pad_light: {e}")

    def set_pattern(
        self,
        pattern: List[int],
        color_idx: int,
        brightness: int = BRIGHTNESS_BRIGHT
    ) -> None:
        """
        Set 16-pad pattern

        Args:
            pattern: List of 16 integers (0 = off, 1 = on)
            color_idx: Color palette index for all lit pads
            brightness: Brightness level
        """
        if len(pattern) != PAD_COUNT:
            logger.warning(f"[{self.serial}] Pattern must have {PAD_COUNT} elements")
            return

        with self.lock:
            for pad_idx in range(PAD_COUNT):
                if pattern[pad_idx] == 0:
                    self.led_buffer[PAD_LED_OFFSET + pad_idx] = 0
                else:
                    value = (color_idx << COLOR_INDEX_SHIFT) | (brightness & BRIGHTNESS_MASK)
                    self.led_buffer[PAD_LED_OFFSET + pad_idx] = value

            try:
                self.device.write(self.led_buffer)
            except OSError as e:
                logger.warning(f"[{self.serial}] Failed to write pattern: {e}")
            except Exception as e:
                logger.error(f"[{self.serial}] Unexpected error in set_pattern: {e}")

    def set_all_pads(
        self,
        color_idx: int,
        brightness: int = BRIGHTNESS_BRIGHT
    ) -> None:
        """
        Set all pads to the same color

        Args:
            color_idx: Color palette index
            brightness: Brightness level
        """
        pattern = [1] * PAD_COUNT
        self.set_pattern(pattern, color_idx, brightness)

    def clear(self) -> None:
        """Clear all pads (turn off all LEDs)"""
        with self.lock:
            for i in range(PAD_COUNT):
                self.led_buffer[PAD_LED_OFFSET + i] = 0

            try:
                self.device.write(self.led_buffer)
            except OSError as e:
                logger.warning(f"[{self.serial}] Failed to clear: {e}")
            except Exception as e:
                logger.error(f"[{self.serial}] Unexpected error in clear: {e}")

    def show_device_number(
        self,
        device_number: int,
        color_idx: int = 11,  # Cyan by default
        duration: float = 1.0
    ) -> None:
        """
        Show device number by lighting up N pads (visual identification)

        Args:
            device_number: Device number (1-4)
            color_idx: Color to use (default: Cyan)
            duration: How long to show (seconds)
        """
        import time

        # Pattern: light up top-left pads based on device number
        # 1 = top-left pad, 2 = top 2 pads, 3 = top 3 pads, 4 = entire top row
        pad_patterns = {
            1: [12],              # 1 пэд
            2: [12, 13],          # 2 пэда
            3: [12, 13, 14],      # 3 пэда
            4: [12, 13, 14, 15],  # 4 пэда (весь верхний ряд)
        }

        pads = pad_patterns.get(device_number, [12])

        # Light up pads
        for pad in pads:
            self.set_pad_light(pad, color_idx, brightness=BRIGHTNESS_BRIGHT, on=True)

        time.sleep(duration)

        # Clear
        self.clear()

    def read_pads(self, timeout_ms: int = 5) -> List[int]:
        """
        Read pressed pads

        Args:
            timeout_ms: Read timeout in milliseconds

        Returns:
            List of pressed pad indices (0-15)
        """
        try:
            data = self.device.read(HID_READ_SIZE, timeout_ms)
        except OSError as e:
            logger.warning(f"[{self.serial}] Read failed: {e}")
            return []
        except Exception as e:
            logger.error(f"[{self.serial}] Unexpected error in read_pads: {e}")
            return []

        if not data or data[0] != 0x02:
            return []

        pressed = []

        # Parse events in 3-byte triplets: [pad_idx, event_byte, velocity_low]
        for i in range(1, len(data), 3):
            if i + 2 >= len(data):
                break

            pad_idx = data[i]
            event_byte = data[i + 1]

            # Check for end marker
            if pad_idx == 0 and event_byte == 0:
                break

            event_type = event_byte & 0xf0

            if event_type == PadEventType.NOTE_ON:
                if 0 <= pad_idx < PAD_COUNT:
                    pressed.append(pad_idx)

        return pressed

    def read_pads_with_velocity(self, timeout_ms: int = 5) -> List[tuple]:
        """
        Read pressed pads with velocity information

        Args:
            timeout_ms: Read timeout in milliseconds

        Returns:
            List of tuples (pad_idx, velocity, event_type)
            velocity is 7-bit MIDI velocity (0-127)
        """
        try:
            data = self.device.read(HID_READ_SIZE, timeout_ms)
        except OSError as e:
            logger.warning(f"[{self.serial}] Read failed: {e}")
            return []
        except Exception as e:
            logger.error(f"[{self.serial}] Unexpected error in read_pads_with_velocity: {e}")
            return []

        if not data or data[0] != 0x02:
            return []

        events = []

        for i in range(1, len(data), 3):
            if i + 2 >= len(data):
                break

            pad_idx = data[i]
            event_byte = data[i + 1]
            velocity_low = data[i + 2]

            if pad_idx == 0 and event_byte == 0:
                break

            event_type = event_byte & 0xf0

            if 0 <= pad_idx < PAD_COUNT:
                # Convert 12-bit velocity to 7-bit MIDI velocity
                velocity_12bit = ((event_byte & 0x0f) << 8) | velocity_low
                velocity = min(127, velocity_12bit >> 5)

                events.append((pad_idx, velocity, event_type))

        return events

    def close(self) -> None:
        """Close device connection and cleanup"""
        if self.device:
            try:
                self.clear()
                self.device.close()
                if self.debug:
                    logger.info(f"[{self.serial}] Closed")
            except Exception as e:
                logger.error(f"[{self.serial}] Error during close: {e}")


def find_devices(max_count: int = 4, debug: bool = False) -> List[MaschineDevice]:
    """
    Find and connect to Maschine Mikro MK3 devices

    Args:
        max_count: Maximum number of devices to connect
        debug: Enable debug logging

    Returns:
        List of connected MaschineDevice instances
    """
    device_infos = [
        d for d in hid.enumerate()
        if d['vendor_id'] == VENDOR_ID and d['product_id'] == PRODUCT_ID
    ][:max_count]

    if not device_infos:
        logger.warning("No Maschine Mikro MK3 devices found")
        return []

    logger.info(f"Found {len(device_infos)} device(s)")

    devices = []
    for info in device_infos:
        device = MaschineDevice(info, debug=debug)
        if device.connect():
            devices.append(device)
        else:
            logger.warning(f"Failed to connect device: {info['serial_number']}")

    logger.info(f"Successfully connected {len(devices)} device(s)")
    return devices


def close_all_devices(devices: List[MaschineDevice]) -> None:
    """
    Close all devices and cleanup

    Args:
        devices: List of MaschineDevice instances
    """
    for device in devices:
        device.close()


def setup_devices_with_config(
    max_count: int = 4,
    debug: bool = False,
    show_numbers: bool = True,
    show_duration: float = 1.0
) -> List[tuple]:
    """
    Setup devices with configuration and visual identification

    This function:
    1. Finds all connected devices
    2. Sorts them by saved configuration (~/.maschine_device_config.json)
    3. Optionally shows device numbers visually (1-4 pads lit)

    Args:
        max_count: Maximum number of devices
        debug: Enable debug logging
        show_numbers: Show device numbers visually on pads
        show_duration: How long to show numbers (seconds)

    Returns:
        List of tuples: [(device, device_num), ...] sorted by device_num

    Example:
        >>> sorted_devices = setup_devices_with_config()
        >>> for device, num in sorted_devices:
        ...     print(f"Device {num}: {device.serial}")
    """
    from .device_config import sort_devices_by_config, has_config

    # Find devices
    devices = find_devices(max_count=max_count, debug=debug)

    if not devices:
        return []

    # Sort by configuration
    sorted_devices = sort_devices_by_config(devices)

    # Show device numbers visually
    if show_numbers:
        import time
        for device, device_num in sorted_devices:
            device.show_device_number(device_num, duration=show_duration)
            time.sleep(0.1)  # Small delay between devices

    # Show configuration status
    if not has_config():
        logger.warning("⚠️  Device configuration not found. Run: python3 device_setup.py")
        logger.info("Using discovery order for device numbers.")

    return sorted_devices

