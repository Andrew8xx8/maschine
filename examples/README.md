# Maschine Mikro MK3 Examples

Simple, focused examples demonstrating different aspects of the MK3 controller.

## Examples

### 1. simple_monitor.py

**Purpose:** Minimal pad event monitoring without LED control.

**Features:**
- Device discovery and connection
- Basic initialization handshake
- Pad event decoding
- Clean, commented code (~90 lines)

**Usage:**
```bash
python simple_monitor.py
```

**Good for:**
- Learning the basics
- Starting point for custom applications
- Understanding the minimal requirements

---

### 2. led_demo.py

**Purpose:** Demonstrate the complete LED color palette system.

**Features:**
- All 17 colors from the palette
- 3 brightness levels (Dim, Normal, Bright)
- Sequential pad lighting
- Clean demonstration of LED protocol

**Usage:**
```bash
python led_demo.py
```

**Good for:**
- Understanding the color palette
- Testing LED functionality
- Visualizing brightness levels
- Learning LED buffer structure

---

## Running the Examples

All examples assume you have:

1. **Installed dependencies:**
   ```bash
   cd /Users/avk/p/maschine
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Killed NIHardwareAgent** (macOS/Linux):
   ```bash
   killall NIHardwareAgent
   ```

3. **Connected your Maschine Mikro MK3** via USB

---

## Building Your Own

These examples are designed to be:
- **Self-contained** - Each file is independent
- **Well-commented** - Explanation of each section
- **Minimal** - Only essential code, easy to understand
- **Modifiable** - Good starting points for your own projects

### Template Structure

```python
#!/usr/bin/env python3
"""Your description here"""

import hid
import time
import os

# Constants
VENDOR_ID = 0x17cc
PRODUCT_ID = 0x1700

def init_device(device):
    """Initialize device with handshakes"""
    # ... initialization code ...
    pass

def main():
    """Main program logic"""
    # 1. Find device
    # 2. Connect
    # 3. Initialize
    # 4. Event loop
    pass

if __name__ == "__main__":
    main()
```

---

## Next Steps

After exploring these examples, check out:

- **maschine_controller.py** - Full-featured multi-device controller
- **PROTOCOL.md** - Complete protocol documentation
- **test_mk3_correct.py** - Protocol verification and testing

## Questions?

See the main README.md for troubleshooting and additional information.

