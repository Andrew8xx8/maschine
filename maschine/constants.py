"""
Константы протокола Maschine Mikro MK3
========================================

Все магические числа, константы устройства и протокола в одном месте.
"""

# ============================================================================
# Device Identifiers
# ============================================================================

VENDOR_ID = 0x17cc
"""Native Instruments USB Vendor ID"""

PRODUCT_ID = 0x1700
"""Maschine Mikro MK3 Product ID"""

MAX_DEVICES = 4
"""Maximum number of devices supported"""

# ============================================================================
# HID Report IDs
# ============================================================================

REPORT_ID_REGISTRATION = 0x03
"""NHL (Native Hardware Library) registration handshake"""

REPORT_ID_LED_CONTROL = 0x80
"""LED control command"""

REPORT_ID_PAD_EVENT = 0x02
"""Incoming pad events"""

# ============================================================================
# LED Buffer Layout
# ============================================================================

LED_REPORT_ID = 0x80
"""Report ID for LED control (same as REPORT_ID_LED_CONTROL)"""

LED_BUFFER_SIZE = 81
"""Total size of LED buffer in bytes"""

LED_BUTTON_OFFSET = 0
"""Offset for button LEDs in buffer"""

PAD_LED_OFFSET = 40
"""Offset for pad LEDs in buffer (pads 0-15 at bytes 40-55)"""

LED_SLIDER_OFFSET = 56
"""Offset for slider LEDs in buffer"""

# ============================================================================
# Color Encoding
# ============================================================================

COLOR_INDEX_SHIFT = 2
"""Bit shift for color index in LED value"""

BRIGHTNESS_MASK = 0b11
"""Bit mask for brightness in LED value"""

# LED value format: (color_index << 2) | (brightness & 0b11)

# ============================================================================
# Brightness Levels
# ============================================================================

BRIGHTNESS_OFF = 0x00
"""LED completely off"""

BRIGHTNESS_DIM = 0x7c
"""Dimmed brightness"""

BRIGHTNESS_NORMAL = 0x7e
"""Normal brightness"""

BRIGHTNESS_BRIGHT = 0x7f
"""Maximum brightness"""

# ============================================================================
# Color Palette (MK3 uses palette indices, not direct RGB!)
# ============================================================================

class Color:
    """
    MK3 Color Palette

    Based on maschine-mikro-mk3-driver/crates/maschine_library/src/lights.rs

    Usage:
        from maschine.constants import Color
        device.set_pad_light(0, Color.RED)
    """
    OFF = 0
    RED = 1
    ORANGE = 2
    LIGHT_ORANGE = 3
    WARM_YELLOW = 4
    YELLOW = 5
    LIME = 6
    GREEN = 7
    MINT = 8
    CYAN = 9
    TURQUOISE = 10
    BLUE = 11
    PLUM = 12
    VIOLET = 13
    PURPLE = 14
    MAGENTA = 15
    FUCHSIA = 16
    WHITE = 17


# Color palette mapping (for reference)
COLOR_NAMES = {
    0: "Off",
    1: "Red",
    2: "Orange",
    3: "Light Orange",
    4: "Warm Yellow",
    5: "Yellow",
    6: "Lime",
    7: "Green",
    8: "Mint",
    9: "Cyan",
    10: "Turquoise",
    11: "Blue",
    12: "Plum",
    13: "Violet",
    14: "Purple",
    15: "Magenta",
    16: "Fuchsia",
    17: "White",
}

# ============================================================================
# Pad Event Types
# ============================================================================

class PadEventType:
    """
    Pad event types from HID protocol

    Based on maschine-mikro-mk3-driver/crates/maschine_library/src/controls.rs
    """
    PRESS_ON = 0x00
    """Pad pressed (pressure start)"""

    NOTE_ON = 0x10
    """Pad note on (above velocity threshold)"""

    PRESS_OFF = 0x20
    """Pad released"""

    NOTE_OFF = 0x30
    """Pad note off"""

    AFTERTOUCH = 0x40
    """Pad aftertouch (pressure change while held)"""


# ============================================================================
# Pad Layout
# ============================================================================

PAD_COUNT = 16
"""Number of pads per device"""

# Physical pad layout (top view, controller facing you):
#    ┌─────────────────────┐
#    │  0   1   2   3  │  <- Top row (farthest from you)
#    │  4   5   6   7  │
#    │  8   9  10  11  │
#    │ 12  13  14  15  │  <- Bottom row (closest to you)
#    └─────────────────────┘

PAD_LAYOUT = """
Physical pad layout (top view):
    ┌─────────────────────┐
    │  0   1   2   3  │  <- Top row
    │  4   5   6   7  │
    │  8   9  10  11  │
    │ 12  13  14  15  │  <- Bottom row
    └─────────────────────┘
"""

# ============================================================================
# Initialization Sequences
# ============================================================================

def get_nhl_registration_msg(client_id: bytes) -> list:
    """
    Generate NHL registration handshake message

    Args:
        client_id: 8-byte unique client identifier

    Returns:
        64-byte HID message
    """
    return [REPORT_ID_REGISTRATION, 0x01] + list(client_id) + [0x00] * 54


INIT_SEQUENCES = [
    [0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00] + [0x00] * 56,
    [0x04, 0x00, 0x01, 0x00, 0x00, 0x00] + [0x00] * 58,
    [REPORT_ID_LED_CONTROL, 0x00] + [0x00] * 62,
]
"""Wake-up sequences sent after registration"""

# ============================================================================
# Timing Constants
# ============================================================================

INIT_DELAY_SHORT = 0.03
"""Short delay between init sequences (seconds)"""

INIT_DELAY_LONG = 0.05
"""Long delay after all init sequences (seconds)"""

REGISTRATION_DELAY = 0.05
"""Delay after NHL registration (seconds)"""

# ============================================================================
# Buffer Sizes
# ============================================================================

HID_READ_SIZE = 64
"""Maximum size for HID read operations"""

HID_WRITE_SIZE = 64
"""Standard size for HID write operations"""

