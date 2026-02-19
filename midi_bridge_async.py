#!/usr/bin/env python3
"""
🎹 Maschine MK3 → MIDI Bridge (Per-Device Ports)
================================================================

Each controller gets its own virtual MIDI port — zero shared state,
zero lock contention, fully parallel operation with 4 devices.

DAW sees: "Maschine MK3 MIDI 1", "Maschine MK3 MIDI 2", etc.

Architecture per device (3 threads):
- Read thread: HID read → parse events → batch MIDI send
- LED thread:  waits for signal → coalesces → single HID write
- Main thread: signal handling, lifecycle

Key optimizations:
- Per-device MIDI ports: no shared lock, no contention
- Batch MIDI: all events from one HID packet sent together
- Deferred LED: HID writes off the critical read path
- Dirty flag: LED written only if buffer changed

Использование:
    python3 midi_bridge_async.py              # Запустить bridge
    python3 midi_bridge_async.py --no-led     # Без LED feedback (макс. производительность)
    python3 midi_bridge_async.py --debug      # Показать все события (диагностика)
    python3 midi_bridge_async.py --setup      # Настроить порядок устройств
    python3 midi_bridge_async.py --show       # Показать конфигурацию
    python3 midi_bridge_async.py --reset-midi # Сбросить фантомные MIDI порты (CoreMIDI)

Требует: pip install python-rtmidi
"""

import math
import time
import sys
import signal
import threading
import atexit
import subprocess
from pathlib import Path
from maschine import (
    setup_devices_with_config,
    PadEventType,
    Color,
    PAD_COUNT,
    BRIGHTNESS_BRIGHT,
    load_device_config,
    save_device_config,
    get_config_path,
    # MIDI utilities
    PAD_TO_NOTE,
    OCTAVE_BANKS,
    BUTTON_LED_MAP,
    note_to_name,
    display_logo_on_devices,
    setup_device_mapping_interactive,
)
from maschine.constants import (
    PAD_LED_OFFSET,
    COLOR_INDEX_SHIFT,
    BRIGHTNESS_MASK,
)

try:
    import rtmidi
except ImportError:
    print("❌ Ошибка: rtmidi не установлен")
    print("\nУстановите:")
    print("  pip install python-rtmidi")
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

MIDI_PORT_NAME = "Maschine MK3 MIDI"
LOGO_PATH = Path(__file__).parent / "logo.png"
LOGO_THRESHOLD = 110
MAX_DEVICES = 4
VELOCITY_THRESHOLD = 5

# Performance tuning
HID_READ_TIMEOUT_MS = 10  # 10ms (was 1ms) - reduces empty syscalls
LED_FEEDBACK_ENABLED = True  # Can be disabled via --no-led flag
DEBUG_MODE = False  # Enable via --debug flag

# Visual feedback: per-pad color map for each bank
#
# User pad numbering (on the controller, 1-indexed from bottom-left):
#   ┌─────────────────────┐
#   │ 13  14  15  16  │  ← top row (far from you)
#   │  9  10  11  12  │
#   │  5   6   7   8  │
#   │  1   2   3   4  │  ← bottom row (close to you)
#   └─────────────────────┘
#
# Driver pad_idx (0-based, from top-left):
#   ┌─────────────────────┐
#   │  0   1   2   3  │  ← top row
#   │  4   5   6   7  │
#   │  8   9  10  11  │
#   │ 12  13  14  15  │  ← bottom row
#   └─────────────────────┘
#
# Mapping: user pad N → pad_idx:
#   1→12  2→13  3→14  4→15    (bottom row)
#   5→8   6→9   7→10  8→11
#   9→4  10→5  11→6  12→7
#  13→0  14→1  15→2  16→3    (top row)

_R = Color.RED
_Y = Color.YELLOW
_O = Color.ORANGE
_G = Color.GREEN
_B = Color.BLUE
_V = Color.VIOLET
_C = Color.CYAN
_M = Color.MAGENTA
_W = Color.WHITE
__ = Color.OFF



def _user_to_idx(colors_by_user_pad):
    """Convert 16 colors in user pad order (1-16) to driver pad_idx order (0-15)"""
    # User row 4 (top):    pads 13,14,15,16 → idx 0,1,2,3
    # User row 3:          pads  9,10,11,12 → idx 4,5,6,7
    # User row 2:          pads  5, 6, 7, 8 → idx 8,9,10,11
    # User row 1 (bottom): pads  1, 2, 3, 4 → idx 12,13,14,15
    u = colors_by_user_pad
    return [
        u[12], u[13], u[14], u[15],  # idx 0-3   ← user pads 13-16 (top)
        u[8],  u[9],  u[10], u[11],  # idx 4-7   ← user pads 9-12
        u[4],  u[5],  u[6],  u[7],   # idx 8-11  ← user pads 5-8
        u[0],  u[1],  u[2],  u[3],   # idx 12-15 ← user pads 1-4 (bottom)
    ]


BANK_PAD_COLORS = {
    #                 user pad: 1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16
    'PAD_MODE': _user_to_idx([ _R, _O, _Y, __, _G, _G, _G, _G, _B, _B, _B, __, _V, _V, __, __]),
    #                          1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16
    'KEYBOARD': _user_to_idx([ _G, _V, _R, __, _G, _V, _O, __, _G, _V, _Y, __, _G, _V, __, __]),
    'CHORDS':   _user_to_idx([ _V, _V, _V, _V, _V, _V, _V, _V, _V, _V, _V, _V, _V, _V, _V, _V]),
    'STEP':     _user_to_idx([ _G, _G, _G, _G, _G, _G, _G, _G, _G, _G, _G, _G, _G, _G, _G, _G]),
}

PAD_ACTIVE_COLOR = Color.WHITE
VELOCITY_HARD_THRESHOLD = 80  # velocity >= this → white flash, below → bank color


# =============================================================================
# Velocity Curves — precomputed lookup tables (zero runtime cost)
# =============================================================================

def _build_lut(func):
    """Precompute 4096-entry lookup table at startup"""
    return bytes(func(v) for v in range(4096))

_LUT_LINEAR = _build_lut(lambda v: min(127, v >> 5))
_LUT_SOFT   = _build_lut(lambda v: min(127, math.isqrt(v * 4)))
_LUT_HARD   = _build_lut(lambda v: min(127, (v * v) >> 17))
_LUT_FIXED  = bytes([127] * 4096)

# Buttons: PERFORM(12), NOTES(13), GROUP(14), AUTO(15) — data[2] bits 4-7
VELOCITY_CURVES = (
    ('LINEAR', 12, 0x10, _LUT_LINEAR),   # PERFORM → Linear
    ('SOFT',   13, 0x20, _LUT_SOFT),     # NOTES   → Soft
    ('HARD',   14, 0x40, _LUT_HARD),     # GROUP   → Hard
    ('FIXED',  15, 0x80, _LUT_FIXED),    # AUTO    → Fixed 127
)


# =============================================================================
# Helper functions
# =============================================================================

def reset_midi():
    """Reset CoreMIDI to clear ghost/phantom MIDI ports from crashed sessions"""
    print("🔄 Сброс CoreMIDI...")
    print("   Это удалит все фантомные MIDI порты от предыдущих сессий.")
    print()

    try:
        subprocess.run(
            ["sudo", "killall", "coremidiserver"],
            check=True,
            timeout=10,
        )
        print("✅ CoreMIDI перезапущен")
        print("   Фантомные порты удалены. Живые порты появятся заново.")
    except subprocess.CalledProcessError:
        # coremidiserver not running — nothing to kill
        print("✅ coremidiserver не запущен, ничего сбрасывать не нужно")
    except FileNotFoundError:
        print("❌ Команда sudo не найдена")
    except subprocess.TimeoutExpired:
        print("❌ Таймаут — попробуйте вручную: sudo killall coremidiserver")


def show_config():
    """Show current configuration"""
    config = load_device_config()

    if not config:
        print("❌ Конфигурация не найдена")
        print(f"   Запустите: python3 {sys.argv[0]} --setup")
        return

    print("\n" + "=" * 60)
    print("📋 Текущая конфигурация устройств")
    print("=" * 60)
    print()

    sorted_serials = sorted(config.items(), key=lambda x: x[1])
    for serial, device_num in sorted_serials:
        print(f"  Device {device_num} → Serial: {serial}")

    print()
    print(f"📁 Файл: {get_config_path()}")
    print()


# =============================================================================
# DeviceBridge - Optimized with batch LED updates
# =============================================================================

class DeviceBridge:
    """
    MIDI bridge for a single device with its own MIDI port.

    Each device gets a dedicated virtual MIDI port — zero lock contention.
    LED buffer is updated in memory, flushed by a dedicated thread.
    """

    def __init__(self, device, device_num, led_enabled=True):
        self.device = device
        self.device_num = device_num
        self.midi_channel = 0  # Each device has its own port, use channel 0
        self.midi_out = None
        self.port_name = f"{MIDI_PORT_NAME} {device_num}"
        self.active_notes = set()
        self.running = False
        self.thread = None
        self.led_enabled = led_enabled

        # Octave bank state
        self.current_bank = 'PAD_MODE'
        self.octave_offset = OCTAVE_BANKS[self.current_bank]
        self.pad_colors = BANK_PAD_COLORS.get(self.current_bank, [Color.ORANGE] * PAD_COUNT)

        # Velocity curve (default: LINEAR) — LUT for zero-cost lookup
        self._vel_curve_idx = 0
        self._vel_lut = VELOCITY_CURVES[0][3]

        # LED state tracking (dirty flag pattern + dedicated thread)
        self._led_dirty = False
        self._led_event = threading.Event()
        self._led_thread = None

    def open_midi_port(self):
        """Create a dedicated virtual MIDI port for this device"""
        self.close_midi_port()
        self.midi_out = rtmidi.MidiOut()
        self.midi_out.open_virtual_port(self.port_name)

    def close_midi_port(self):
        """Close this device's MIDI port and release the rtmidi object"""
        if self.midi_out:
            try:
                self.midi_out.close_port()
            except Exception:
                pass
            try:
                del self.midi_out
            except Exception:
                pass
            self.midi_out = None

    def start(self):
        """Start reading thread and LED thread"""
        self.running = True

        # Use blocking reads so timeout_ms is honored (avoid busy spin).
        try:
            self.device.device.set_nonblocking(False)
        except OSError:
            pass

        if self.led_enabled:
            # Init pads + bank LEDs + curve LED before starting LED thread
            self._init_pads()
            self._update_bank_leds()
            self._update_curve_leds()
            self._flush_lights()
            # Start dedicated LED thread for runtime updates
            self._led_thread = threading.Thread(target=self._led_loop, daemon=True)
            self._led_thread.start()

        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def _init_pads(self):
        """Initialize all pads to current bank color map (batch write)"""
        for pad_idx in range(PAD_COUNT):
            color = self.pad_colors[pad_idx]
            bright = BRIGHTNESS_BRIGHT if color != Color.OFF else 0
            self._update_pad_buffer(pad_idx, color, bright)
        self._flush_lights()

    def _update_pad_buffer(self, pad_idx, color_idx, brightness):
        """
        Update LED buffer in memory (no HID write).
        Sets dirty flag for later flush.
        """
        if not self.led_enabled:
            return

        if color_idx > 0:
            value = (color_idx << COLOR_INDEX_SHIFT) | (brightness & BRIGHTNESS_MASK)
        else:
            value = 0

        # Only mark dirty if value actually changed
        current = self.device.led_buffer[PAD_LED_OFFSET + pad_idx]
        if current != value:
            self.device.led_buffer[PAD_LED_OFFSET + pad_idx] = value
            self._led_dirty = True

    def _flush_lights(self):
        """
        Write LED buffer to device (single HID write).
        Only writes if buffer was modified (dirty flag).
        Called from LED thread or during init (before threads start).
        """
        if not self.led_enabled or not self._led_dirty:
            return

        # Clear dirty BEFORE write so changes during write re-set it
        self._led_dirty = False
        try:
            self.device.device.write(self.device.led_buffer)
        except Exception:
            pass

    def _led_loop(self):
        """
        Dedicated LED flush thread.
        Waits for signal from read loop, coalesces rapid updates.
        This keeps HID LED writes off the critical read path.
        """
        while self.running:
            # Wait for signal or timeout (coalesce rapid updates)
            self._led_event.wait(timeout=0.05)
            self._led_event.clear()
            self._flush_lights()

    def set_velocity_curve(self, curve_idx):
        """Switch velocity curve and update button LEDs"""
        if curve_idx == self._vel_curve_idx:
            return
        if not (0 <= curve_idx < len(VELOCITY_CURVES)):
            return

        name, _, _, lut = VELOCITY_CURVES[curve_idx]
        self._vel_curve_idx = curve_idx
        self._vel_lut = lut

        if DEBUG_MODE:
            print(f"🎚️  D{self.device_num} Velocity curve: {name}")

        if self.led_enabled:
            self._update_curve_leds()
            if self._led_dirty:
                self._led_event.set()

    def _update_curve_leds(self):
        """Update FIXED VEL button LED only (buffer only)"""
        if not self.led_enabled:
            return

        # FIXED VEL button LED: on when curve is not LINEAR
        self.device.led_buffer[1 + 26] = 0x7f if self._vel_curve_idx != 0 else 0x00
        self._led_dirty = True

    def set_octave_bank(self, bank_name):
        """Switch octave bank and update pad colors"""
        if bank_name not in OCTAVE_BANKS:
            return

        self.all_notes_off()
        self.current_bank = bank_name
        self.octave_offset = OCTAVE_BANKS[bank_name]
        self.pad_colors = BANK_PAD_COLORS.get(bank_name, [Color.ORANGE] * PAD_COUNT)

        if self.led_enabled:
            self._update_bank_leds()
            for pad_idx in range(PAD_COUNT):
                color = self.pad_colors[pad_idx]
                bright = BRIGHTNESS_BRIGHT if color != Color.OFF else 0
                self._update_pad_buffer(pad_idx, color, bright)
            if self._led_dirty:
                self._led_event.set()

    def _update_bank_leds(self):
        """Update bank button LEDs (buffer only, caller must trigger flush)"""
        if not self.led_enabled:
            return

        for _, led_idx in BUTTON_LED_MAP.items():
            self.device.led_buffer[1 + led_idx] = 0x00

        led_idx = BUTTON_LED_MAP.get(self.current_bank)
        if led_idx is not None:
            self.device.led_buffer[1 + led_idx] = 0x7f

        self._led_dirty = True

    def stop(self):
        """Stop reading and LED threads"""
        self.running = False
        self._led_event.set()  # Wake LED thread so it can exit
        if self._led_thread:
            self._led_thread.join(timeout=1.0)
        if self.thread:
            self.thread.join(timeout=1.0)

    def _read_loop(self):
        """
        Main read loop - optimized with batch MIDI + deferred LED writes.

        Pattern:
        1. Read HID packet
        2. Parse ALL events → collect MIDI messages + update LED buffer
        3. Send all MIDI messages (no lock — dedicated port per device)
        4. Signal LED thread to flush (non-blocking)
        """
        button_states = {}

        # Cache instance attrs as locals — avoids self.X dict lookup per event
        hid_dev = self.device.device
        active_notes = self.active_notes
        midi_out = self.midi_out
        midi_ch = self.midi_channel
        led_event = self._led_event
        update_pad = self._update_pad_buffer
        vel_lut = self._vel_lut
        pad_colors = self.pad_colors
        octave_offset = self.octave_offset
        note_off_cmd = 0x80 + midi_ch
        note_on_cmd = 0x90 + midi_ch

        # Pre-extract constants as locals
        _NOTE_ON = PadEventType.NOTE_ON
        _PRESS_OFF = PadEventType.PRESS_OFF
        _NOTE_OFF = PadEventType.NOTE_OFF
        _VEL_THR = VELOCITY_THRESHOLD
        _VEL_HARD = VELOCITY_HARD_THRESHOLD
        _WHITE = PAD_ACTIVE_COLOR
        _BRIGHT = BRIGHTNESS_BRIGHT
        _PAD_COUNT = PAD_COUNT
        _OFF = Color.OFF
        _debug = DEBUG_MODE
        _timeout = HID_READ_TIMEOUT_MS

        while self.running:
            try:
                data = hid_dev.read(64, timeout_ms=_timeout)
            except Exception:
                time.sleep(0.001)
                continue

            if not data or len(data) < 1:
                time.sleep(0.001)
                continue

            report_id = data[0]

            # ============================================================
            # Report 0x01: Button Events
            # ============================================================
            if report_id == 0x01:
                if len(data) < 6:
                    continue

                # --- Octave bank buttons (data[4]) ---
                b4 = data[4]

                bank_checks = (
                    ('PAD_MODE', 27, b4 & 0x08),
                    ('KEYBOARD', 28, b4 & 0x10),
                    ('CHORDS', 29, b4 & 0x20),
                    ('STEP', 30, b4 & 0x40),
                )

                for bank_name, button_idx, is_pressed in bank_checks:
                    was_pressed = button_states.get(button_idx, False)
                    is_pressed = is_pressed != 0

                    if is_pressed and not was_pressed:
                        self.set_octave_bank(bank_name)
                        # Refresh cached locals after bank switch
                        pad_colors = self.pad_colors
                        octave_offset = self.octave_offset

                    button_states[button_idx] = is_pressed

                # --- FIXED VEL button (data[4] bit 2) → round-robin ---
                fv_pressed = (b4 & 0x04) != 0
                if fv_pressed and not button_states.get(26, False):
                    next_idx = (self._vel_curve_idx + 1) % len(VELOCITY_CURVES)
                    self.set_velocity_curve(next_idx)
                    vel_lut = self._vel_lut
                button_states[26] = fv_pressed

                # --- Velocity curve direct select (data[2]) ---
                b2 = data[2]

                for curve_idx, (_, btn_idx, mask, _) in enumerate(VELOCITY_CURVES):
                    is_pressed = (b2 & mask) != 0
                    was_pressed = button_states.get(btn_idx, False)

                    if is_pressed and not was_pressed:
                        self.set_velocity_curve(curve_idx)
                        vel_lut = self._vel_lut

                    button_states[btn_idx] = is_pressed

            # ============================================================
            # Report 0x02: Pad Events (batch MIDI + deferred LED)
            # ============================================================
            elif report_id == 0x02:
                midi_batch = []
                _data = data  # local alias

                for i in range(1, len(_data), 3):
                    if i + 2 >= len(_data):
                        break

                    pad_idx = _data[i]
                    event_byte = _data[i + 1]
                    velocity_low = _data[i + 2]

                    if pad_idx == 0 and event_byte == 0 and velocity_low == 0:
                        break

                    event_type = event_byte & 0xf0

                    if pad_idx >= _PAD_COUNT:
                        continue

                    velocity = vel_lut[((event_byte & 0x0f) << 8) | velocity_low]

                    note = PAD_TO_NOTE.get(pad_idx)
                    if note is None:
                        continue
                    note += octave_offset

                    # Press events
                    if event_type == _NOTE_ON:
                        if _debug:
                            note_name = note_to_name(note)
                            if velocity < _VEL_THR:
                                print(f"⚠️  D{self.device_num} Pad {pad_idx:2d}→{note_name} v{velocity:3d} FILTERED (< {_VEL_THR})")
                            else:
                                print(f"🎵 D{self.device_num} Pad {pad_idx:2d}→{note_name} v{velocity:3d}")

                        if velocity < _VEL_THR:
                            continue

                        if note in active_notes:
                            midi_batch.append([note_off_cmd, note, 0])
                        midi_batch.append([note_on_cmd, note, velocity])
                        active_notes.add(note)

                        if velocity >= _VEL_HARD:
                            update_pad(pad_idx, _WHITE, _BRIGHT)
                        else:
                            update_pad(pad_idx, pad_colors[pad_idx], _BRIGHT)

                    # Release events
                    elif event_type == _PRESS_OFF or event_type == _NOTE_OFF:
                        if note in active_notes:
                            midi_batch.append([note_off_cmd, note, 0])
                            active_notes.discard(note)

                        rc = pad_colors[pad_idx]
                        update_pad(pad_idx, rc, _BRIGHT if rc != _OFF else 0)

                # Send all MIDI messages (no lock — dedicated port per device)
                if midi_batch:
                    _send = midi_out.send_message
                    for msg in midi_batch:
                        _send(msg)

                # Signal LED thread (non-blocking)
                if self._led_dirty:
                    led_event.set()

    def send_note_on(self, note, velocity):
        """Send MIDI Note On with re-trigger (no lock — dedicated port)"""
        if self.midi_out and velocity > 0:
            if note in self.active_notes:
                self.midi_out.send_message([0x80 + self.midi_channel, note, 0])
            self.midi_out.send_message([0x90 + self.midi_channel, note, velocity])
            self.active_notes.add(note)

    def send_note_off(self, note):
        """Send MIDI Note Off"""
        if self.midi_out and note in self.active_notes:
            self.midi_out.send_message([0x80 + self.midi_channel, note, 0])
            self.active_notes.discard(note)

    def all_notes_off(self):
        """Turn off all active notes"""
        for note in list(self.active_notes):
            self.send_note_off(note)


# =============================================================================
# MIDIBridge - Coordinator
# =============================================================================

class MIDIBridge:
    """
    MIDI bridge coordinator.

    Each device gets its own virtual MIDI port — fully independent,
    zero lock contention, zero shared state between devices.
    DAW sees: "Maschine MK3 MIDI 1", "Maschine MK3 MIDI 2", etc.
    """

    def __init__(self, devices, config=None, led_enabled=True):
        self.devices = devices
        self.config = config or {}
        self.running = False
        self.device_bridges = []
        self.led_enabled = led_enabled

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup_ports)

    def _signal_handler(self, signum, frame):
        print("\n\n🛑 Остановка...")
        self.running = False

    def _cleanup_ports(self):
        """atexit handler: close all MIDI ports to prevent ghost ports in CoreMIDI"""
        for bridge in self.device_bridges:
            bridge.close_midi_port()

    def setup_midi(self):
        """Create per-device MIDI ports and device bridges"""
        try:
            sorted_devices = []

            if self.config:
                for device in self.devices:
                    device_num = self.config.get(device.serial)
                    if device_num:
                        sorted_devices.append((device, device_num))

                sorted_devices.sort(key=lambda x: x[1])

                print("📋 Используется сохраненная конфигурация:")
            else:
                print("⚠️  Конфигурация не найдена, используется порядок обнаружения:")
                for i, device in enumerate(self.devices, 1):
                    sorted_devices.append((device, i))

                print(f"\n💡 Совет: запустите `python3 {sys.argv[0]} --setup` для постоянной привязки")

            print(f"   LED feedback: {'Enabled (batch writes)' if self.led_enabled else 'Disabled'}")
            print(f"   HID timeout: {HID_READ_TIMEOUT_MS}ms")
            print()

            for device, device_num in sorted_devices:
                bridge = DeviceBridge(device, device_num, self.led_enabled)
                bridge.open_midi_port()
                self.device_bridges.append(bridge)
                print(f"   Device {device_num} [{device.serial}] → '{bridge.port_name}'")

            print()
            return True

        except Exception as e:
            print(f"❌ Ошибка MIDI: {e}")
            # Close any ports already opened
            for bridge in self.device_bridges:
                bridge.close_midi_port()
            return False

    def run(self):
        """Main loop"""
        self.running = True

        print("🎹 MIDI Bridge (Per-Device Ports)")
        print("=" * 60)
        print(f"Устройств: {len(self.device_bridges)}")
        print(f"Velocity threshold: {VELOCITY_THRESHOLD}")
        print(f"LED feedback: {'Batch writes' if self.led_enabled else 'Disabled'}")
        print(f"HID read timeout: {HID_READ_TIMEOUT_MS}ms")
        print("=" * 60)
        print()

        print("⚡ Запуск потоков...")
        for bridge in self.device_bridges:
            bridge.start()
        print("✅ Работаю!\n")

        try:
            while self.running:
                time.sleep(0.1)

        finally:
            print("\n🛑 Остановка...")
            for bridge in self.device_bridges:
                bridge.stop()

            print("\n   Очистка...")
            for bridge in self.device_bridges:
                bridge.all_notes_off()
                bridge.device.clear()
                bridge.close_midi_port()

            print("✅ Завершено")


# =============================================================================
# Main
# =============================================================================

def main():
    global LED_FEEDBACK_ENABLED, DEBUG_MODE

    # Parse arguments
    if '--show' in sys.argv:
        show_config()
        return

    if '--reset-midi' in sys.argv:
        reset_midi()
        return

    if '--no-led' in sys.argv:
        LED_FEEDBACK_ENABLED = False

    if '--debug' in sys.argv:
        DEBUG_MODE = True

    setup_mode = '--setup' in sys.argv

    print("=" * 60)
    print("🎹 Maschine MK3 → MIDI Bridge (Async/Optimized)")
    print("=" * 60)
    print()

    if DEBUG_MODE:
        print("🔍 DEBUG режим включен — показываю все события")
        print()

    if not LED_FEEDBACK_ENABLED:
        print("⚡ LED feedback отключен (максимальная производительность)")
        print()

    sorted_devices = setup_devices_with_config(
        max_count=MAX_DEVICES,
        show_numbers=True,
        show_duration=0.5
    )

    if not sorted_devices:
        print("❌ Устройства не найдены")
        print("\n1. Подключите Maschine Mikro MK3")
        print("2. killall NIHardwareAgent")
        return

    devices = []
    config = {}
    for device, device_num in sorted_devices:
        devices.append(device)
        config[device.serial] = device_num

    print(f"✅ Найдено: {len(devices)} устройств")
    for device, device_num in sorted_devices:
        print(f"   Device {device_num}: {device.serial}")
    print()

    if display_logo_on_devices(devices, LOGO_PATH, LOGO_THRESHOLD):
        print(f"✅ Логотип отображён на {len(devices)} устройствах")
    print()

    if setup_mode:
        new_config = setup_device_mapping_interactive(devices, MAX_DEVICES)
        if not new_config:
            print("❌ Настройка не завершена")
            for device in devices:
                device.close()
            return
        if save_device_config(new_config):
            config = new_config

    bridge = MIDIBridge(devices, config, led_enabled=LED_FEEDBACK_ENABLED)

    if not bridge.setup_midi():
        for device in devices:
            device.close()
        return

    try:
        bridge.run()
    finally:
        for device in devices:
            device.close()
        print("✅ Закрыто\n")


if __name__ == "__main__":
    main()
