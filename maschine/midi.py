"""
MIDI utilities for Maschine Mikro MK3
=====================================

Common MIDI mappings, constants, and helper functions.
"""

from pathlib import Path
from typing import Optional, List

from .constants import Color, BRIGHTNESS_BRIGHT, PAD_COUNT
from .screen import Screen

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# =============================================================================
# Pad to MIDI Note Mapping
# =============================================================================

# Physical pad layout (top-left = 12, bottom-right = 3):
#   12  13  14  15
#    8   9  10  11
#    4   5   6   7
#    0   1   2   3
#
# MIDI notes (base octave C1-D#2, notes 36-51):
#   C1  C#1  D1  D#1
#   E1  F1  F#1  G1
#   G#1 A1  A#1  B1
#   C2  C#2 D2  D#2

PAD_TO_NOTE = {
    12: 36, 13: 37, 14: 38, 15: 39,  # Top row
    8: 40, 9: 41, 10: 42, 11: 43,    # Second row
    4: 44, 5: 45, 6: 46, 7: 47,      # Third row
    0: 48, 1: 49, 2: 50, 3: 51,      # Bottom row
}

# Reverse mapping: note -> pad
NOTE_TO_PAD = {v: k for k, v in PAD_TO_NOTE.items()}


# =============================================================================
# Octave Banks
# =============================================================================

# Octave banks for switching note ranges
# Each bank adds an offset to the base notes (36-51)
OCTAVE_BANKS = {
    'PAD_MODE': 0,     # C1-D#2   (notes 36-51)  - base octave
    'KEYBOARD': 16,    # E2-G3    (notes 52-67)  - +16 semitones
    'CHORDS': 32,      # G#3-B4   (notes 68-83)  - +32 semitones
    'STEP': 48,        # C5-D#6   (notes 84-99)  - +48 semitones
}

# Button LED indices for bank buttons
BUTTON_LED_MAP = {
    'PAD_MODE': 27,
    'KEYBOARD': 28,
    'CHORDS': 29,
    'STEP': 30,
}


# =============================================================================
# Note Conversion
# =============================================================================

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_to_name(note: int) -> str:
    """
    Convert MIDI note number to note name.

    Args:
        note: MIDI note number (0-127)

    Returns:
        Note name string (e.g., "C4", "F#3")

    Example:
        >>> note_to_name(60)
        'C4'
        >>> note_to_name(36)
        'C1'
    """
    octave = (note // 12) - 1
    note_name = NOTE_NAMES[note % 12]
    return f"{note_name}{octave}"


def name_to_note(name: str) -> Optional[int]:
    """
    Convert note name to MIDI note number.

    Args:
        name: Note name (e.g., "C4", "F#3")

    Returns:
        MIDI note number or None if invalid

    Example:
        >>> name_to_note("C4")
        60
        >>> name_to_note("C1")
        36
    """
    if len(name) < 2:
        return None

    # Handle sharps
    if '#' in name:
        note_part = name[:2]
        octave_part = name[2:]
    else:
        note_part = name[0]
        octave_part = name[1:]

    try:
        note_idx = NOTE_NAMES.index(note_part.upper())
        octave = int(octave_part)
        return (octave + 1) * 12 + note_idx
    except (ValueError, IndexError):
        return None


# =============================================================================
# Logo / Image Display
# =============================================================================

def load_image_to_screen(
    image_path: str,
    threshold: int = 128
) -> Optional[Screen]:
    """
    Load an image and convert it to a Screen object.

    Args:
        image_path: Path to image file
        threshold: Brightness threshold for black/white conversion (0-255)

    Returns:
        Screen object with loaded image, or None if failed
    """
    if not HAS_PIL:
        return None

    try:
        img = Image.open(image_path)
        img = img.convert('L')  # Grayscale
        img = img.resize((128, 32), Image.Resampling.LANCZOS)

        screen = Screen()
        screen.clear()

        pixels = img.load()
        for y in range(32):
            for x in range(128):
                if pixels[x, y] > threshold:
                    screen.set_pixel(x, y, on=True)

        return screen
    except Exception:
        return None


def display_logo_on_devices(
    devices: List,
    logo_path: Path,
    threshold: int = 110
) -> bool:
    """
    Display logo image on all devices.

    Args:
        devices: List of MaschineDevice instances
        logo_path: Path to logo image
        threshold: Brightness threshold for conversion

    Returns:
        True if successful, False otherwise
    """
    if not HAS_PIL or not logo_path.exists():
        return False

    try:
        screen = load_image_to_screen(str(logo_path), threshold)
        if screen:
            for device in devices:
                screen.write(device.device)
            return True
    except Exception:
        pass

    return False


# =============================================================================
# Interactive Setup
# =============================================================================

# =============================================================================
# Pad Display (16x4 grid across 4 devices)
# =============================================================================

# Compact 2x4 font for pad display (fits ~7 chars in 16px)
# Each char is 2px wide + 1px spacing = 3px per char
PAD_FONT_COMPACT = {
    'A': [[1,1], [1,1], [1,1], [1,1]],
    'B': [[1,1], [1,1], [1,1], [1,1]],
    'C': [[1,1], [1,0], [1,0], [1,1]],
    'D': [[1,1], [1,1], [1,1], [1,1]],
    'E': [[1,1], [1,1], [1,0], [1,1]],
    'F': [[1,1], [1,1], [1,0], [1,0]],
    'G': [[1,1], [1,0], [1,1], [1,1]],
    'H': [[1,1], [1,1], [1,1], [1,1]],
    'I': [[1,1], [0,1], [0,1], [1,1]],
    'J': [[0,1], [0,1], [1,1], [1,1]],
    'K': [[1,1], [1,1], [1,0], [1,1]],
    'L': [[1,0], [1,0], [1,0], [1,1]],
    'M': [[1,1], [1,1], [1,1], [1,1]],
    'N': [[1,1], [1,1], [1,1], [1,1]],
    'O': [[1,1], [1,1], [1,1], [1,1]],
    'P': [[1,1], [1,1], [1,1], [1,0]],
    'Q': [[1,1], [1,1], [1,1], [0,1]],
    'R': [[1,1], [1,1], [1,1], [1,1]],
    'S': [[1,1], [1,0], [0,1], [1,1]],
    'T': [[1,1], [0,1], [0,1], [0,1]],
    'U': [[1,1], [1,1], [1,1], [1,1]],
    'V': [[1,1], [1,1], [1,1], [0,1]],
    'W': [[1,1], [1,1], [1,1], [1,1]],
    'X': [[1,1], [0,1], [0,1], [1,1]],
    'Y': [[1,1], [1,1], [0,1], [0,1]],
    'Z': [[1,1], [0,1], [1,0], [1,1]],
    '0': [[1,1], [1,1], [1,1], [1,1]],
    '1': [[0,1], [0,1], [0,1], [0,1]],
    '2': [[1,1], [0,1], [1,0], [1,1]],
    '3': [[1,1], [0,1], [0,1], [1,1]],
    '4': [[1,1], [1,1], [0,1], [0,1]],
    '5': [[1,1], [1,0], [0,1], [1,1]],
    '6': [[1,1], [1,0], [1,1], [1,1]],
    '7': [[1,1], [0,1], [0,1], [0,1]],
    '8': [[1,1], [1,1], [1,1], [1,1]],
    '9': [[1,1], [1,1], [0,1], [1,1]],
    ' ': [[0], [0], [0], [0]],  # 1 wide space
    '.': [[0], [0], [0], [1]],
    '!': [[1], [1], [0], [1]],
    '-': [[0,0], [1,1], [0,0], [0,0]],
    ':': [[0], [1], [0], [1]],
}

# Standard 3x4 font for pad display (fits ~4 chars in 16px)
PAD_FONT = {
    'A': [[0,1,0], [1,0,1], [1,1,1], [1,0,1]],
    'B': [[1,1,0], [1,1,1], [1,0,1], [1,1,0]],
    'C': [[0,1,1], [1,0,0], [1,0,0], [0,1,1]],
    'D': [[1,1,0], [1,0,1], [1,0,1], [1,1,0]],
    'E': [[1,1,1], [1,1,0], [1,0,0], [1,1,1]],
    'F': [[1,1,1], [1,1,0], [1,0,0], [1,0,0]],
    'G': [[0,1,1], [1,0,0], [1,0,1], [0,1,1]],
    'H': [[1,0,1], [1,1,1], [1,1,1], [1,0,1]],
    'I': [[1,1,1], [0,1,0], [0,1,0], [1,1,1]],
    'J': [[0,0,1], [0,0,1], [1,0,1], [0,1,0]],
    'K': [[1,0,1], [1,1,0], [1,1,0], [1,0,1]],
    'L': [[1,0,0], [1,0,0], [1,0,0], [1,1,1]],
    'M': [[1,0,1], [1,1,1], [1,0,1], [1,0,1]],
    'N': [[1,0,1], [1,1,1], [1,1,1], [1,0,1]],
    'O': [[0,1,0], [1,0,1], [1,0,1], [0,1,0]],
    'P': [[1,1,0], [1,0,1], [1,1,0], [1,0,0]],
    'Q': [[0,1,0], [1,0,1], [1,1,1], [0,1,1]],
    'R': [[1,1,0], [1,0,1], [1,1,0], [1,0,1]],
    'S': [[0,1,1], [1,0,0], [0,0,1], [1,1,0]],
    'T': [[1,1,1], [0,1,0], [0,1,0], [0,1,0]],
    'U': [[1,0,1], [1,0,1], [1,0,1], [0,1,0]],
    'V': [[1,0,1], [1,0,1], [1,0,1], [0,1,0]],
    'W': [[1,0,1], [1,0,1], [1,1,1], [1,0,1]],
    'X': [[1,0,1], [0,1,0], [0,1,0], [1,0,1]],
    'Y': [[1,0,1], [0,1,0], [0,1,0], [0,1,0]],
    'Z': [[1,1,1], [0,0,1], [0,1,0], [1,1,1]],
    '0': [[0,1,0], [1,0,1], [1,0,1], [0,1,0]],
    '1': [[0,1,0], [1,1,0], [0,1,0], [1,1,1]],
    '2': [[1,1,0], [0,0,1], [0,1,0], [1,1,1]],
    '3': [[1,1,0], [0,1,0], [0,0,1], [1,1,0]],
    '4': [[1,0,1], [1,0,1], [1,1,1], [0,0,1]],
    '5': [[1,1,1], [1,0,0], [0,1,1], [1,1,0]],
    '6': [[0,1,1], [1,0,0], [1,1,1], [0,1,0]],
    '7': [[1,1,1], [0,0,1], [0,1,0], [0,1,0]],
    '8': [[0,1,0], [1,0,1], [0,1,0], [1,0,1]],
    '9': [[0,1,0], [1,1,1], [0,0,1], [1,1,0]],
    ' ': [[0,0], [0,0], [0,0], [0,0]],  # 2 wide space
    '.': [[0], [0], [0], [1]],  # 1 wide
    '!': [[1], [1], [0], [1]],  # 1 wide
    '-': [[0,0,0], [0,0,0], [1,1,1], [0,0,0]],
    ':': [[0], [1], [0], [1]],  # 1 wide
}


def text_to_pad_bitmap(text: str, compact: bool = False) -> List[List[int]]:
    """
    Convert text to 4-row bitmap for pad display.

    Args:
        text: Text to convert (uppercase recommended)
        compact: Use compact 2x4 font (fits ~7 chars) instead of 3x4 (fits ~4 chars)

    Returns:
        List of 4 rows, each row is a list of 0/1 values

    Example:
        >>> bitmap = text_to_pad_bitmap("HI")
        >>> len(bitmap)  # 4 rows
        4
    """
    font = PAD_FONT_COMPACT if compact else PAD_FONT
    columns = []

    for char in text.upper():
        if char in font:
            char_data = font[char]
            width = len(char_data[0])

            # Add each column of the character
            for col_idx in range(width):
                col = [char_data[row][col_idx] for row in range(4)]
                columns.append(col)

            # Add 1-pixel spacing between characters
            columns.append([0, 0, 0, 0])

    # Remove trailing space if any
    if columns and columns[-1] == [0, 0, 0, 0]:
        columns.pop()

    # Convert columns to rows
    if not columns:
        return [[0]*16 for _ in range(4)]

    # Transpose: columns -> rows
    rows = []
    for row_idx in range(4):
        row = [columns[col_idx][row_idx] if col_idx < len(columns) else 0
               for col_idx in range(max(16, len(columns)))]
        rows.append(row)

    return rows


def get_text_width(text: str, compact: bool = False) -> int:
    """
    Calculate pixel width of text.

    Args:
        text: Text to measure
        compact: Use compact 2x4 font

    Returns:
        Width in pixels (columns)
    """
    font = PAD_FONT_COMPACT if compact else PAD_FONT
    width = 0
    for char in text.upper():
        if char in font:
            width += len(font[char][0]) + 1  # char width + spacing
    return max(0, width - 1)  # Remove trailing space


def display_text_on_pads(
    devices: List,
    text: str,
    color,
    center: bool = True,
    brightness: int = 0x7f,
    compact: bool = False
) -> None:
    """
    Display static text across 4 devices (16x4 pad grid).

    Args:
        devices: List of 4 MaschineDevice instances (in order left to right)
        text: Text to display
        color: Color index (use Color.RED, etc.)
        center: Center text horizontally if True
        brightness: LED brightness (0x00-0x7f)
        compact: Use compact 2x4 font (fits ~7 chars) instead of 3x4 (fits ~4 chars)

    Example:
        >>> display_text_on_pads(devices, "HELLO", Color.CYAN)  # 4 chars max
        >>> display_text_on_pads(devices, "HANDSON", Color.CYAN, compact=True)  # 7 chars
    """
    if len(devices) != 4:
        raise ValueError("Requires exactly 4 devices")

    bitmap = text_to_pad_bitmap(text, compact=compact)
    text_width = get_text_width(text, compact=compact)

    # Calculate offset for centering
    offset = 0
    if center and text_width < 16:
        offset = (16 - text_width) // 2

    # Build pattern for each device and write once
    for dev_idx, device in enumerate(devices):
        pattern = [0] * 16
        start_col = dev_idx * 4

        for local_col in range(4):
            global_col = start_col + local_col - offset

            for row in range(4):
                pad_idx = row * 4 + local_col

                # Check if this pixel is lit
                if 0 <= global_col < len(bitmap[row]) and bitmap[row][global_col]:
                    pattern[pad_idx] = 1

        # Single write per device
        device.set_pattern(pattern, color, brightness=brightness)


def setup_device_mapping_interactive(
    devices: List,
    max_devices: int = 4
) -> Optional[dict]:
    """
    Interactive device mapping setup.

    Flashes each device and prompts user to assign a number.

    Args:
        devices: List of MaschineDevice instances
        max_devices: Maximum device number allowed

    Returns:
        Config dict {serial: device_num} or None if cancelled
    """
    import time

    print("\n" + "=" * 60)
    print("🎹 Настройка порядка устройств")
    print("=" * 60)
    print()
    print(f"Найдено устройств: {len(devices)}")
    print()

    config = {}
    used_numbers = set()

    for i, device in enumerate(devices, 1):
        print(f"\n--- Устройство {i}/{len(devices)} ---")
        print(f"Serial: {device.serial}")
        print("⚡ Подсвечиваю устройство...")

        # Flash to identify
        for _ in range(3):
            device.set_all_pads(Color.CYAN, brightness=0x7f)
            time.sleep(0.3)
            device.clear()
            time.sleep(0.2)

        while True:
            try:
                num_str = input(f"\nКакой номер присвоить? (1-{max_devices}): ").strip()
                num = int(num_str)

                if num < 1 or num > max_devices:
                    print(f"❌ Номер должен быть от 1 до {max_devices}")
                    continue

                if num in used_numbers:
                    print(f"❌ Номер {num} уже используется!")
                    continue

                config[device.serial] = num
                used_numbers.add(num)
                print(f"✅ Устройство {device.serial} → Device {num}")
                break

            except ValueError:
                print("❌ Введите число!")
            except KeyboardInterrupt:
                print("\n\n🛑 Настройка отменена")
                return None

    # Show summary
    print("\n" + "=" * 60)
    print("📋 Итоговая конфигурация:")
    print("=" * 60)

    sorted_config = sorted(config.items(), key=lambda x: x[1])
    for serial, num in sorted_config:
        print(f"  Device {num} → {serial}")

    print("\n💾 Сохранить? (y/n): ", end='')

    try:
        answer = input().strip().lower()
        if answer in ['y', 'yes', 'д', 'да', '']:
            return config
    except KeyboardInterrupt:
        print("\n\n🛑 Отменено")

    return None

