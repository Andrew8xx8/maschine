#!/usr/bin/env python3
"""
Maschine Mikro MK3 Multi-Device HID Controller
==============================================

Python driver for Native Instruments Maschine Mikro MK3 controllers.

Features:
  - Multi-device support (up to 4 controllers simultaneously)
  - Pad event detection (pressure-sensitive, 16 pads per device)
  - LED control using MK3's color palette system
  - Automatic pad lighting on events
  - Demo and debug modes

Protocol:
  - HID-based communication (hidapi)
  - Input: Pad events via Report ID 0x02
  - Output: LED control via 81-byte buffer (Report ID 0x80)
  - Color system: Palette-based (17 colors), not direct RGB

Usage:
  python maschine_controller.py              # Basic monitoring with auto-light
  python maschine_controller.py --demo-color # Color demo on all pads
  python maschine_controller.py --debug      # Verbose logging
  python maschine_controller.py --no-auto-light # No automatic lighting

References:
  - Protocol: See PROTOCOL.md for complete technical documentation
  - Based on: github.com/r00tman/maschine-mikro-mk3-driver
"""

import hid
import threading
import time
import os
import argparse
import sys
from dataclasses import dataclass
from typing import Optional, List, Tuple

# Device identifiers
VENDOR_ID = 0x17cc
PRODUCT_ID = 0x1700
MAX_DEVICES = 4

# Pad constants
PAD_COUNT = 16

# Physical pad layout (top view, controller facing you):
#    ┌─────────────────────┐
#    │  0   1   2   3  │  <- Top row (farthest from you)
#    │  4   5   6   7  │
#    │  8   9  10  11  │
#    │ 12  13  14  15  │  <- Bottom row (closest to you)
#    └─────────────────────┘


@dataclass
class PadEvent:
    """Represents a pad hit event"""
    pad_index: int  # 0-15
    velocity: int   # 0-127
    timestamp: float
    device_serial: str


class MaschineDevice:
    """Manages a single Maschine Mikro MK3 device"""

    # LED buffer size (from MK3 driver reference)
    LED_BUFFER_SIZE = 81  # [0x80] + 80 bytes
    PAD_LED_OFFSET = 40  # Pads start at byte 40

    # Color palette (MK3 uses palette, not RGB!)
    COLORS = {
        'OFF': 0, 'RED': 1, 'ORANGE': 2, 'LIGHT_ORANGE': 3,
        'WARM_YELLOW': 4, 'YELLOW': 5, 'LIME': 6, 'GREEN': 7,
        'MINT': 8, 'CYAN': 9, 'TURQUOISE': 10, 'BLUE': 11,
        'PLUM': 12, 'VIOLET': 13, 'PURPLE': 14, 'MAGENTA': 15,
        'FUCHSIA': 16, 'WHITE': 17
    }

    # Brightness levels
    BRIGHTNESS_OFF = 0x00
    BRIGHTNESS_DIM = 0x7c
    BRIGHTNESS_NORMAL = 0x7e
    BRIGHTNESS_BRIGHT = 0x7f

    # Initialization sequences
    INIT_SEQUENCES = [
        [0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00] + [0x00] * 56,
        [0x04, 0x00, 0x01, 0x00, 0x00, 0x00] + [0x00] * 58,
        [0x02, 0x00, 0x01] + [0x00] * 61,
        [0x80, 0x00] + [0x00] * 62,
        [0xa0, 0x00, 0x00, 0x00] + [0x00] * 60,
        [0x01, 0x00, 0x00, 0x02] + [0x00] * 60,
        [0x03, 0x00, 0x01, 0x00] + [0x00] * 60,
        [0x05, 0x00, 0x01, 0x00] + [0x00] * 60,
    ]

    def __init__(self, device_info: dict, debug: bool = False):
        self.device_info = device_info
        self.serial = device_info['serial_number']
        self.debug = debug
        self.device: Optional[hid.device] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.pad_callback = None
        self.last_active_pad: Optional[int] = None

        # LED buffer: 81 bytes [Report ID][Button LEDs][Pad LEDs][Slider LEDs]
        # Pads: bytes 40-55 (16 pads, 1 byte each = color palette + brightness)
        self.led_buffer = [0x00] * self.LED_BUFFER_SIZE
        self.led_buffer[0] = 0x80  # Report ID for LED control

    def connect(self) -> bool:
        """Connect to the device and initialize"""
        try:
            self.device = hid.device()
            self.device.open_path(self.device_info['path'])

            manufacturer = self.device.get_manufacturer_string()
            product = self.device.get_product_string()
            print(f"[{self.serial}] Connected: {manufacturer} {product}")

            # Send registration handshake
            client_id = os.urandom(8)
            register_msg = [0x03, 0x01] + list(client_id) + [0x00] * 54
            self.device.write(register_msg)
            if self.debug:
                print(f"[{self.serial}] NHL Registration: client_id={client_id.hex()}")

            time.sleep(0.2)

            # Send initialization sequences
            if self.debug:
                print(f"[{self.serial}] Sending {len(self.INIT_SEQUENCES)} handshakes...")

            for i, init_seq in enumerate(self.INIT_SEQUENCES, 1):
                try:
                    self.device.write(init_seq)
                    if self.debug:
                        header = ' '.join(f'{b:02x}' for b in init_seq[:8])
                        print(f"[{self.serial}]   Handshake #{i}: [{header}...]")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[{self.serial}]   Handshake #{i} failed: {e}")

            self.device.set_nonblocking(True)
            print(f"[{self.serial}] ✅ Initialized successfully")
            return True

        except Exception as e:
            print(f"[{self.serial}] ❌ Connection failed: {e}")
            return False

    def set_pad_color(self, pad_index: int, r: int, g: int, b: int):
        """
        Set pad color using MK3's palette system

        Note: MK3 uses a 17-color palette (not direct RGB). This function
        automatically maps RGB values to the nearest palette color and
        derives brightness from the RGB intensity.

        Protocol:
            LED value = (color_index << 2) | (brightness & 0b11)
            Buffer offset = PAD_LED_OFFSET (40) + pad_index

        Args:
            pad_index: Pad number (0-15)
            r, g, b: RGB values (0-255) - mapped to nearest palette color
        """
        if not self.device or pad_index < 0 or pad_index >= PAD_COUNT:
            return

        # Map RGB to nearest palette color
        color_idx, brightness = self._rgb_to_palette(r, g, b)

        # Calculate LED value
        if brightness == self.BRIGHTNESS_OFF:
            val = 0
        else:
            val = (color_idx << 2) + (brightness & 0b11)

        # Update buffer at correct offset
        self.led_buffer[self.PAD_LED_OFFSET + pad_index] = val

        # Write entire LED buffer
        try:
            self.device.write(self.led_buffer)

            if self.debug:
                print(f"[{self.serial}] Pad {pad_index+1} -> color_idx={color_idx}, brightness=0x{brightness:02x}")
        except Exception as e:
            if self.debug:
                print(f"[{self.serial}] Set pad color failed: {e}")

    def _rgb_to_palette(self, r: int, g: int, b: int) -> Tuple[int, int]:
        """
        Map RGB to nearest MK3 palette color and brightness

        Simple heuristic-based mapping:
          - Determines dominant color component (R/G/B)
          - Maps to closest palette entry
          - Derives brightness from maximum RGB value

        Returns:
            tuple: (color_index, brightness) where:
                - color_index: 0-17 (palette index)
                - brightness: 0x00 (off), 0x7c (dim), 0x7e (normal), 0x7f (bright)
        """
        # If all zeros, off
        if r == 0 and g == 0 and b == 0:
            return (self.COLORS['OFF'], self.BRIGHTNESS_OFF)

        # Calculate brightness from max RGB component
        max_val = max(r, g, b)
        if max_val < 64:
            brightness = self.BRIGHTNESS_DIM
        elif max_val < 192:
            brightness = self.BRIGHTNESS_NORMAL
        else:
            brightness = self.BRIGHTNESS_BRIGHT

        # Simple color mapping based on dominant component
        if r > g and r > b:
            if g > 128:
                color = self.COLORS['ORANGE'] if g > b else self.COLORS['YELLOW']
            elif b > 128:
                color = self.COLORS['MAGENTA']
            else:
                color = self.COLORS['RED']
        elif g > r and g > b:
            if r > 128:
                color = self.COLORS['YELLOW']
            elif b > 128:
                color = self.COLORS['CYAN']
            else:
                color = self.COLORS['GREEN']
        elif b > r and b > g:
            if r > 128:
                color = self.COLORS['MAGENTA']
            elif g > 128:
                color = self.COLORS['CYAN']
            else:
                color = self.COLORS['BLUE']
        else:
            # Equal components = white-ish
            color = self.COLORS['WHITE']

        return (color, brightness)

    def set_all_pads(self, r: int, g: int, b: int):
        """Set all pads to the same color"""
        color_idx, brightness = self._rgb_to_palette(r, g, b)

        if brightness == self.BRIGHTNESS_OFF:
            val = 0
        else:
            val = (color_idx << 2) + (brightness & 0b11)

        # Update all pads in buffer
        for pad in range(PAD_COUNT):
            self.led_buffer[self.PAD_LED_OFFSET + pad] = val

        # Write once
        try:
            self.device.write(self.led_buffer)
        except Exception as e:
            if self.debug:
                print(f"[{self.serial}] Set all pads failed: {e}")

    def clear_pad(self, pad_index: int):
        """Turn off a specific pad"""
        if pad_index < 0 or pad_index >= PAD_COUNT:
            return

        self.led_buffer[self.PAD_LED_OFFSET + pad_index] = 0

        try:
            self.device.write(self.led_buffer)
        except Exception as e:
            if self.debug:
                print(f"[{self.serial}] Clear pad failed: {e}")

    def decode_pad_event(self, data: List[int]) -> Optional[PadEvent]:
        """
        Decode HID packet into pad event

        Args:
            data: HID packet data

        Returns:
            PadEvent if valid pad data, None otherwise
        """
        if len(data) >= 3 and data[0] == 0x02:
            pad_index = data[1]
            velocity = data[2]

            if velocity > 0 and pad_index < PAD_COUNT:
                return PadEvent(
                    pad_index=pad_index,
                    velocity=velocity,
                    timestamp=time.time(),
                    device_serial=self.serial
                )
        return None

    def listen_loop(self):
        """Main event listening loop"""
        self.running = True
        print(f"[{self.serial}] 🎧 Listening for events...")

        while self.running:
            try:
                data = self.device.read(64)

                if data:
                    if self.debug:
                        hex_str = ' '.join(f'{b:02x}' for b in data[:16])
                        print(f"[{self.serial}] RAW ({len(data)} bytes): {hex_str}...")

                    event = self.decode_pad_event(data)
                    if event:
                        print(f"[{self.serial}] 🎵 Pad {event.pad_index + 1} hit with velocity {event.velocity}")

                        # Call callback if registered
                        if self.pad_callback:
                            self.pad_callback(self, event)

                time.sleep(0.001)  # 1ms polling

            except Exception as e:
                if self.debug:
                    print(f"[{self.serial}] Read error: {e}")
                time.sleep(0.1)

    def start_listening(self):
        """Start listening thread"""
        if not self.device:
            return False

        self.thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        """Stop listening and disconnect"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.device:
            try:
                # Turn off all LEDs
                self.set_all_pads(0, 0, 0)
                self.device.close()
            except:
                pass
        print(f"[{self.serial}] Disconnected")


class MaschineController:
    """Manages multiple Maschine devices"""

    def __init__(self, debug: bool = False, auto_light: bool = True):
        self.debug = debug
        self.auto_light = auto_light
        self.devices: List[MaschineDevice] = []

    def scan_devices(self) -> int:
        """Scan for connected Maschine devices"""
        print("\n🔍 Scanning for Maschine Mikro MK3 devices...")

        device_infos = []
        for dev in hid.enumerate():
            if dev['vendor_id'] == VENDOR_ID and dev['product_id'] == PRODUCT_ID:
                if self.debug:
                    print(f"\n  Found interface:")
                    print(f"    Serial: {dev.get('serial_number', 'N/A')}")
                    print(f"    Interface: {dev.get('interface_number', 'N/A')}")
                    print(f"    Usage Page: 0x{dev.get('usage_page', 0):04x}")
                device_infos.append(dev)

        print(f"\nFound {len(device_infos)} device(s)")

        # Connect to each device
        connected = 0
        for info in device_infos[:MAX_DEVICES]:
            device = MaschineDevice(info, debug=self.debug)
            if device.connect():
                device.pad_callback = self.on_pad_event
                self.devices.append(device)
                connected += 1

        print(f"\n✅ Successfully connected to {connected}/{len(device_infos)} device(s)\n")
        return connected

    def on_pad_event(self, device: MaschineDevice, event: PadEvent):
        """Handle pad events with optional lighting"""
        if not self.auto_light:
            return

        # Clear previous pad if exists
        if device.last_active_pad is not None:
            device.clear_pad(device.last_active_pad)

        # Light up current pad based on velocity
        brightness = min(255, int(event.velocity * 2))  # Scale velocity to brightness
        device.set_pad_color(event.pad_index, 0, brightness, 0)  # Green
        device.last_active_pad = event.pad_index

    def start_all(self):
        """Start listening on all devices"""
        for device in self.devices:
            device.start_listening()

        print(f"🎧 Listening to {len(self.devices)} controller(s)")
        print("Press Ctrl+C to exit\n")

    def demo_colors(self):
        """Demo mode: cycle through colors on all pads"""
        print("🌈 Color demo mode - cycling through all pads...")

        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 128, 0),  # Orange
            (128, 0, 255),  # Purple
        ]

        try:
            for color_idx, (r, g, b) in enumerate(colors):
                print(f"Color {color_idx + 1}/{len(colors)}: RGB({r},{g},{b})")

                for device in self.devices:
                    for pad in range(PAD_COUNT):
                        device.set_pad_color(pad, r, g, b)
                        time.sleep(0.02)

                time.sleep(1)

            # Clear all
            print("Clearing all pads...")
            for device in self.devices:
                device.set_all_pads(0, 0, 0)

        except KeyboardInterrupt:
            print("\nDemo interrupted")

    def stop_all(self):
        """Stop all devices"""
        print("\n\n🛑 Shutting down...")
        for device in self.devices:
            device.stop()


def main():
    parser = argparse.ArgumentParser(
        description='Maschine Mikro MK3 Multi-Device Controller'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output (raw packets)'
    )
    parser.add_argument(
        '--demo-color',
        action='store_true',
        help='Run color demo mode (cycle through colors)'
    )
    parser.add_argument(
        '--no-auto-light',
        action='store_true',
        help='Disable automatic pad lighting on hit'
    )

    args = parser.parse_args()

    # Initialize controller
    controller = MaschineController(
        debug=args.debug,
        auto_light=not args.no_auto_light
    )

    # Scan and connect devices
    connected = controller.scan_devices()

    if connected == 0:
        print("❌ No devices connected. Exiting.")
        print("\nTroubleshooting:")
        print("1. Ensure devices are connected via USB")
        print("2. Kill NIHardwareAgent: killall NIHardwareAgent")
        print("3. Try running with sudo if permission errors occur")
        sys.exit(1)

    # Demo mode or normal operation
    if args.demo_color:
        controller.demo_colors()
    else:
        controller.start_all()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    controller.stop_all()
    print("Goodbye! 👋\n")


if __name__ == "__main__":
    main()

