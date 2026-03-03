#!/usr/bin/env python3
"""
Pad Trainer — finger drumming practice on Maschine Mikro MK3
=============================================================

Architecture: 3 threads
  - Read thread:  HID input → pad hits (MIDI + scoring) / button flags
  - LED thread:   coalesced HID LED writes on signal
  - Main thread:  state machine, metronome tick (~1kHz), countdown, screen

State machine:
  LESSON_SELECT  — pick an exercise by pressing a colored pad
  EX_IDLE        — exercise loaded, free play (MIDI on pad press)
  EX_DEMO        — pattern plays 1 loop (sound + pad flash + metronome)
  EX_COUNTDOWN   — 4-beat count-in → EX_PLAYING
  EX_PLAYING     — user plays, loop meter grades timing

Transitions:
  LESSON_SELECT  → pad press → EX_IDLE
  EX_IDLE        → REC       → EX_DEMO (1 loop → back to EX_IDLE)
  EX_IDLE        → PLAY      → EX_COUNTDOWN → EX_PLAYING
  EX_PLAYING     → STOP      → EX_IDLE
  EX_IDLE        → STOP      → LESSON_SELECT

Controls:
  PAD MODE / KEYBOARD / CHORDS / STEP — switch bank (Beginner / Intermediate / Pro / Virtuoso)
  PLAY  — start exercise (count-in → play)
  REC   — demo pattern (1 loop preview)
  STOP  — back one level
  ENCODER push — toggle BPM adjust (in EX_IDLE), turn to change ±1

MIDI:
  Creates virtual MIDI port "Pad Trainer MIDI" — route it in DAW.
  Each bank sends on its own MIDI channel (1-4), metronome on ch 10.

Usage:
    python3 pad_trainer.py                    # Run
    python3 pad_trainer.py --list             # List exercises
    python3 pad_trainer.py --setup            # Configure device order
    python3 pad_trainer.py --student NAME     # Track progress (stats/name.jsonl)
    python3 pad_trainer.py lesson.json        # Load custom JSON exercise

NOTE: Stop midi_bridge_async.py before running — same HID device.
"""

import json
import math
import time
import sys
import signal
import threading
from datetime import datetime
from pathlib import Path

from maschine import (
    setup_devices_with_config,
    PadEventType,
    Color,
    PAD_COUNT,
    BRIGHTNESS_DIM,
    BRIGHTNESS_BRIGHT,
    save_device_config,
    display_logo_on_devices,
    load_image_to_screen,
    setup_device_mapping_interactive,
    Screen,
)
from maschine.constants import (
    PAD_LED_OFFSET,
    LED_SLIDER_OFFSET,
    COLOR_INDEX_SHIFT,
    BRIGHTNESS_MASK,
)
from maschine.screen_font import draw_text_5x7


# Optional: MIDI output
try:
    import rtmidi
except ImportError:
    print("❌ python-rtmidi не установлен")
    print("   pip install python-rtmidi")
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

MAX_DEVICES = 4
LOGO_PATH = Path(__file__).parent / "logo.png"


# =============================================================================
# Button indices (from Rust driver controls.rs)
# =============================================================================

BTN_PLAY     = 22
BTN_REC      = 23
BTN_STOP     = 24

BTN_SHIFT    = 25
BTN_PAD_MODE = 27
BTN_KEYBOARD = 28
BTN_CHORDS   = 29
BTN_STEP     = 30

EXERCISES_PER_BANK = 16
BANK_BUTTONS = (
    (BTN_PAD_MODE, 0),   # Beat (Level I)
    (BTN_KEYBOARD, 1),   # Live (Level II)
    (BTN_CHORDS,   2),   # Pro (optional)
    (BTN_STEP,     3),   # Drums (Level III)
)
BANK_NAMES = ('Beat (I)', 'Live (II)', 'Pro (opt)', 'Drums (III)')

# Button N → HID report 0x01 byte index and bit mask (pre-computed)
def _btn_byte_mask(btn_id):
    return 1 + btn_id // 8, 1 << (btn_id % 8)

_BTN_MAP = {
    btn: _btn_byte_mask(btn)
    for btn in (BTN_PLAY, BTN_REC, BTN_STOP, BTN_SHIFT,
                BTN_PAD_MODE, BTN_KEYBOARD, BTN_CHORDS, BTN_STEP)
}


# =============================================================================
# Pad numbering: user (1-16, bottom-left) ↔ driver (0-15, top-left)
# =============================================================================

_USER_TO_IDX = [
    None,
    12, 13, 14, 15,   # user 1-4   → bottom row
     8,  9, 10, 11,   # user 5-8
     4,  5,  6,  7,   # user 9-12
     0,  1,  2,  3,   # user 13-16 → top row
]

# Loop meter: top 2 rows (8 pads) show loop progress
# Row 4 (top): user 13,14,15,16 = indices 0,1,2,3  → loops 1-4
# Row 3:       user 9,10,11,12  = indices 4,5,6,7  → loops 5-8
LOOP_METER_PADS = (0, 1, 2, 3, 4, 5, 6, 7)  # 8 pad indices
_LOOP_METER_SET = frozenset(LOOP_METER_PADS)
LOOPS_TO_PASS = 8

_IDX_TO_USER = [0] * 16
for _u in range(1, 17):
    _IDX_TO_USER[_USER_TO_IDX[_u]] = _u


def user_to_idx(user_pad):
    return _USER_TO_IDX[user_pad]



# =============================================================================
# Color helpers
# =============================================================================

COLOR_MAP = {
    'OFF': Color.OFF, 'RED': Color.RED, 'ORANGE': Color.ORANGE,
    'LIGHT_ORANGE': Color.LIGHT_ORANGE, 'WARM_YELLOW': Color.WARM_YELLOW,
    'YELLOW': Color.YELLOW, 'GREEN': Color.GREEN, 'BLUE': Color.BLUE,
    'CYAN': Color.CYAN, 'VIOLET': Color.VIOLET, 'PURPLE': Color.PURPLE,
    'MAGENTA': Color.MAGENTA, 'WHITE': Color.WHITE, 'LIME': Color.LIME,
    'MINT': Color.MINT, 'TURQUOISE': Color.TURQUOISE, 'PLUM': Color.PLUM,
    'FUCHSIA': Color.FUCHSIA,
}


def _led_byte(color_idx, brightness):
    """Encode color + brightness into a single LED buffer byte"""
    if color_idx == 0:
        return 0
    return (color_idx << COLOR_INDEX_SHIFT) | (brightness & BRIGHTNESS_MASK)


# Distinct colors for lesson select pads (one per exercise)
LESSON_COLORS = [
    Color.CYAN, Color.PURPLE, Color.MAGENTA, Color.BLUE,
    Color.VIOLET, Color.TURQUOISE, Color.PLUM, Color.MINT,
    Color.CYAN, Color.PURPLE, Color.MAGENTA, Color.BLUE,
    Color.VIOLET, Color.TURQUOISE, Color.PLUM, Color.MINT,
]


# =============================================================================
# MIDI
# =============================================================================

MIDI_PORT_NAME = "Pad Trainer MIDI"
MIDI_BASE_NOTE = 36  # C1 — fallback if layer has no midi_note

# MIDI status bytes (channel 10 = drums, metronome)
MIDI_NOTE_ON_CH10  = 0x99
MIDI_NOTE_OFF_CH10 = 0x89

# Metronome click on downbeats (every 4 steps), channel 10
METRO_NOTE_ACCENT = 32  # G#0 — beat 1
METRO_NOTE_NORMAL = 33  # A0  — beats 2, 3, 4
METRO_VEL_ACCENT = 100
METRO_VEL_NORMAL = 70

# Color names for console display
_COLOR_EMOJI = {
    Color.OFF: '⬛', Color.RED: '🔴', Color.ORANGE: '🟠',
    Color.YELLOW: '🟡', Color.GREEN: '🟢', Color.BLUE: '🔵',
    Color.CYAN: '🔵', Color.VIOLET: '🟣', Color.PURPLE: '🟣',
    Color.MAGENTA: '🟣', Color.WHITE: '⚪', Color.LIME: '🟢',
    Color.MINT: '🟢', Color.TURQUOISE: '🔵', Color.PLUM: '🟣',
    Color.FUCHSIA: '🟣',
}


def _print_pattern(layer, subdivisions=4, label_width=14):
    """Print a rhythm pattern as a visual grid"""
    name = layer.name.ljust(label_width)
    beats = []
    for s in range(layer.steps):
        if s > 0 and s % subdivisions == 0:
            beats.append('│')
        if layer.hit_at(s):
            v = layer.vel_at(s)
            if v >= 100:
                beats.append('X')  # accent
            elif v >= 60:
                beats.append('x')  # normal
            else:
                beats.append('·')  # ghost
        else:
            beats.append('─')
    return f"  {name} {' '.join(beats)}"


def _print_beat_ruler(steps, subdivisions=4, label_width=14):
    """Print beat numbers above pattern"""
    pad = ' ' * (label_width + 2)
    nums = []
    for s in range(steps):
        if s > 0 and s % subdivisions == 0:
            nums.append(' ')
        if s % subdivisions == 0:
            nums.append(str(s // subdivisions + 1))
        else:
            nums.append(' ')
    return f"{pad} {' '.join(nums)}"


# =============================================================================
# Clock Engine
# =============================================================================

class ClockEngine:
    """BPM clock with step tracking using perf_counter"""

    def __init__(self, bpm, steps, subdivisions=4):
        self.steps = steps
        self.subdivisions = subdivisions
        self.set_bpm(bpm)
        self._origin = 0.0
        self._running = False

    def set_bpm(self, bpm):
        self.bpm = max(40, min(300, bpm))
        self.step_dur = 60.0 / self.bpm / self.subdivisions
        self.loop_dur = self.step_dur * self.steps

    def start(self, origin=None):
        self._origin = origin if origin is not None else time.perf_counter()
        self._running = True

    def stop(self):
        self._running = False

    @property
    def running(self):
        return self._running

    @property
    def elapsed(self):
        return time.perf_counter() - self._origin if self._running else 0.0

    @property
    def current_step(self):
        if not self._running:
            return 0
        return int(self.elapsed / self.step_dur) % self.steps

    @property
    def current_loop(self):
        if not self._running:
            return 0
        return int(self.elapsed / self.loop_dur)

    def step_time(self, step, loop=None):
        """Absolute time when step starts"""
        if loop is None:
            loop = self.current_loop
        return self._origin + loop * self.loop_dur + step * self.step_dur

    def offset_ms(self, hit_time, step, loop=None):
        """Hit timing: negative=early, positive=late"""
        return (hit_time - self.step_time(step, loop)) * 1000.0


# =============================================================================
# Exercise data structures
# =============================================================================

class Layer:
    def __init__(self, data):
        self.name = data.get('name', '?')
        self.user_pad = data['pad']
        self.pad_idx = user_to_idx(self.user_pad)
        self.color = COLOR_MAP.get(data.get('color', 'WHITE'), Color.WHITE)
        self.midi_note = data.get('midi_note', MIDI_BASE_NOTE + self.user_pad - 1)
        self.pattern = data['pattern']
        self.velocities = data.get('velocity',
                                   [100 if h else 0 for h in self.pattern])
        self.hits_per_loop = sum(1 for p in self.pattern if p != 0)
        self.hit_steps = tuple(s for s, p in enumerate(self.pattern) if p != 0)

    @property
    def steps(self):
        return len(self.pattern)

    def hit_at(self, step):
        return self.pattern[step % self.steps] != 0

    def vel_at(self, step):
        return self.velocities[step % self.steps]


class Exercise:
    def __init__(self, data):
        self.name = data.get('name', 'Unnamed')
        self.bpm = data.get('bpm', 90)
        self.steps = data.get('steps', 16)
        self.subdivisions = data.get('subdivisions', 4)
        self.layers = [Layer(l) for l in data['layers']]
        self.timing_ok_ms = data.get('timing_threshold_ms', 45)

    @classmethod
    def from_json(cls, path):
        with open(path) as f:
            return cls(json.load(f))


# =============================================================================
# Hit Tracker — timing statistics
# =============================================================================

class HitTracker:
    """Per-layer timing statistics with pre-allocated loop slots.

    Slots are indexed 0..num_loops-1 and allocated up-front via init_pass().
    No deques, no buffering — callers write directly by slot index.
    """

    def __init__(self, num_loops=LOOPS_TO_PASS):
        self.num_loops = num_loops
        self._loops = {}    # layer_idx → list of dicts
        self._extras = {}   # layer_idx → list of int

    def init_pass(self, num_layers):
        """Pre-allocate empty slots for a new 8-loop pass."""
        for i in range(num_layers):
            self._loops[i] = [{} for _ in range(self.num_loops)]
            self._extras[i] = [0] * self.num_loops

    def record(self, layer_idx, slot, step, offset_ms, velocity):
        if 0 <= slot < self.num_loops:
            self._loops[layer_idx][slot][step] = (offset_ms, velocity)

    def record_extra(self, layer_idx, slot):
        if 0 <= slot < self.num_loops:
            self._extras[layer_idx][slot] += 1

    def spread(self, layer_idx):
        """Std dev of timing offsets across all loops in pass."""
        slots = self._loops.get(layer_idx)
        if not slots:
            return float('inf')
        offsets = [o for d in slots for o, _ in d.values()]
        if len(offsets) < 4:
            return float('inf')
        mean = sum(offsets) / len(offsets)
        return math.sqrt(sum((x - mean) ** 2 for x in offsets) / len(offsets))

    def grade_loop(self, layer_idx, slot, ok_ms, window_ms,
                   expected_hits=0):
        slots = self._loops.get(layer_idx)
        if not slots or slot < 0 or slot >= self.num_loops:
            return None, "no_data"
        loop_data = slots[slot]
        extras = self._extras.get(layer_idx, [0] * self.num_loops)[slot]

        if not loop_data:
            if expected_hits == 0:
                return 'green', "silent"
            return 'red', "0_hits"

        hits = len(loop_data)
        missing = max(0, expected_hits - hits) if expected_hits > 0 else 0

        if missing > 1:
            steps_hit = sorted(loop_data.keys())
            return 'red', f"{hits}/{expected_hits} steps={steps_hit}"

        max_off = max(abs(o) for o, _ in loop_data.values())
        if max_off >= window_ms:
            return 'red', f"max_off={max_off:.0f}ms>={window_ms}"

        if missing == 1:
            steps_hit = sorted(loop_data.keys())
            return 'yellow', f"{hits}/{expected_hits} steps={steps_hit} max={max_off:.0f}ms ex={extras}"

        if max_off < ok_ms and extras <= 1:
            return 'green', f"{hits}h {max_off:.0f}ms"
        return 'yellow', f"{hits}h {max_off:.0f}ms ex={extras}"


# =============================================================================
# Stats Writer — JSONL per-student progress tracking
# =============================================================================

STATS_DIR = Path(__file__).parent / "stats"


class StatsWriter:
    """Appends one JSONL line per completed 8-loop pass."""

    def __init__(self, student_name):
        import re
        self.student = student_name
        self.slug = re.sub(r'[^\w-]', '_', student_name).lower().strip('_')
        STATS_DIR.mkdir(exist_ok=True)
        self.path = STATS_DIR / f"{self.slug}.jsonl"
        self.session = self._next_session()
        self.session_start = datetime.now().isoformat(timespec='seconds')
        self._last_result = self._load_last_results()

    def _next_session(self):
        if not self.path.exists():
            return 1
        max_s = 0
        for line in self.path.open():
            line = line.strip()
            if not line:
                continue
            try:
                max_s = max(max_s, json.loads(line).get('session', 0))
            except json.JSONDecodeError:
                pass
        return max_s + 1

    def write_pass(self, *, exercise_name, exercise_idx, bpm, bpm_after,
                   subdivisions, duration_s, loop_grades, loop_layers):
        greens = sum(1 for g in loop_grades if g == 'green')
        yellows = sum(1 for g in loop_grades if g == 'yellow')
        reds = sum(1 for g in loop_grades if g == 'red')

        record = {
            'student': self.slug,
            'session': self.session,
            'session_start': self.session_start,
            'ts': datetime.now().isoformat(timespec='seconds'),
            'exercise': exercise_name,
            'exercise_idx': exercise_idx,
            'bpm': bpm,
            'bpm_after': bpm_after,
            'subdivisions': subdivisions,
            'duration_s': round(duration_s, 1),
            'loops': [
                {
                    'grade': loop_grades[i],
                    'layers': loop_layers[i],
                }
                for i in range(len(loop_grades))
                if loop_grades[i] is not None
            ],
            'summary': {'greens': greens, 'yellows': yellows, 'reds': reds},
        }
        with self.path.open('a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

        self._last_result[exercise_idx] = (greens, yellows, reds)

    def last_results(self):
        """Return dict: exercise_idx → 'green'/'yellow'/'red' based on last pass."""
        return {idx: self._classify(*counts)
                for idx, counts in self._last_result.items()}

    def _load_last_results(self):
        results = {}
        if not self.path.exists():
            return results
        for line in self.path.open():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                idx = rec.get('exercise_idx')
                s = rec.get('summary', {})
                if idx is not None:
                    results[idx] = (s.get('greens', 0), s.get('yellows', 0), s.get('reds', 0))
            except json.JSONDecodeError:
                pass
        return results

    @staticmethod
    def _classify(greens, yellows, reds):
        total = greens + yellows + reds
        if total == 0:
            return 'red'
        if greens >= total * 0.75:
            return 'green'
        if reds > total * 0.5:
            return 'red'
        return 'yellow'


# =============================================================================
# Renderer — LED control
# =============================================================================

class Renderer:
    """Manages pad LEDs and touch strip.

    Only mutates the in-memory LED buffer. Actual HID writes are
    coalesced by the Trainer's LED thread via _signal_led().
    """

    STRIP_COUNT = 25

    def __init__(self, device):
        self._buf = device.led_buffer

    def _set(self, offset, val):
        if self._buf[offset] != val:
            self._buf[offset] = val

    def pad(self, idx, color, brightness=BRIGHTNESS_BRIGHT):
        self._set(PAD_LED_OFFSET + idx, _led_byte(color, brightness))

    def pad_off(self, idx):
        self._set(PAD_LED_OFFSET + idx, 0)

    def clear_pads(self):
        for i in range(PAD_COUNT):
            self._buf[PAD_LED_OFFSET + i] = 0

    def button_led(self, btn_id, color, brightness=BRIGHTNESS_BRIGHT):
        self._set(1 + btn_id, _led_byte(color, brightness))

    def button_led_off(self, btn_id):
        self._set(1 + btn_id, 0)

    def strip_playhead(self, position):
        """Touch strip as playhead (0.0-1.0)"""
        head = int(position * self.STRIP_COUNT) % self.STRIP_COUNT
        trail = (head - 1) % self.STRIP_COUNT
        base = LED_SLIDER_OFFSET
        for i in range(self.STRIP_COUNT):
            val = 0x7f if i == head else (0x3f if i == trail else 0x00)
            if self._buf[base + i] != val:
                self._buf[base + i] = val

    def strip_clear(self):
        base = LED_SLIDER_OFFSET
        for i in range(self.STRIP_COUNT):
            self._buf[base + i] = 0


# =============================================================================
# Screen Renderer — exercise display on 128x32 OLED
# =============================================================================

class ScreenRenderer:
    """Draws on the 128x32 OLED. Updated only on state transitions.

    LESSON_SELECT → logo image
    Exercise states → pattern grid (no text)
    """

    SCREEN_W = 128

    def __init__(self, logo_path=None):
        self.screen = Screen()
        self._logo_screen = None
        if logo_path and Path(logo_path).exists():
            self._logo_screen = load_image_to_screen(str(logo_path), 110)

    def render_logo(self):
        """Copy pre-loaded logo into screen buffer."""
        if self._logo_screen:
            self.screen.buffer[:] = self._logo_screen.buffer[:]
        else:
            self.screen.clear()

    def render_pattern(self, exercise):
        """Draw pattern grid — no text, full 32px height for rows."""
        scr = self.screen
        scr.clear()

        layers = exercise.layers
        n = len(layers)
        if n == 0:
            return

        step_w = self.SCREEN_W / exercise.steps

        gap = 1
        total_h = 32 - (n - 1) * gap
        row_h = max(2, total_h // n)

        for li, layer in enumerate(layers):
            y = li * (row_h + gap)
            for s in range(exercise.steps):
                if layer.hit_at(s):
                    x = int(s * step_w)
                    w = max(1, int(step_w) - 1)
                    v = layer.vel_at(s)
                    h = row_h if v >= 80 else max(2, row_h - 1)
                    scr.draw_rect(x + 1, y, w, h, filled=True, on=True)
            subs = exercise.subdivisions
            for b in range(1, exercise.steps // subs):
                bx = int(b * subs * step_w)
                scr.set_pixel(bx, y + row_h, True)

    def write(self, device):
        """Send screen buffer to device."""
        self.screen.write(device.device)

    def clear(self, device):
        self.screen.clear()
        self.screen.write(device.device)


# =============================================================================
# Trainer — main exercise runner
# =============================================================================

class Trainer:
    """Runs exercises on one Maschine Mikro MK3.

    3 threads:
      Read thread  — HID input → pad hits (MIDI + scoring) / button flags
      LED thread   — coalesced HID LED writes on signal
      Main thread  — state machine, clock tick (~1kHz), countdown, screen
    """

    HIT_WINDOW_MS = 120.0
    NOTE_DURATION_STEPS = 3
    COUNTDOWN_BEATS = 4

    def __init__(self, device, exercises, debug=False, stats=None):
        self.device = device
        self.exercises = exercises
        self.debug = debug
        self.stats = stats
        self.rend = Renderer(device)
        self.scr = ScreenRenderer(logo_path=LOGO_PATH)
        self.tracker = HitTracker()

        self.midi_out = rtmidi.MidiOut()
        self.midi_out.open_virtual_port(MIDI_PORT_NAME)

        self._pending_offs = []

        self._BTN_ACTIONS = (
            (BTN_PLAY, self._on_play),
            (BTN_STOP, self._on_stop_btn),
            (BTN_REC,  self._on_rec),
        )

        self.exercise = None
        self.clock = None

        self.state = 'LESSON_SELECT'
        self._demo_loops_done = 0
        self._demo_finished = False
        self._last_step = -1
        self._last_loop = -1
        self._btn = {}
        self._pad_layer = {}

        self._hit_protect = {}     # pad_idx → perf_counter expiry
        self._pressed_notes = {}   # pad_idx → midi note
        self._lesson_pad_map = {}  # pad_idx → exercise index
        self._pass_base = 0
        self._pass_start_time = 0.0
        self._exercise_idx = 0

        self._loop_grades = [None] * LOOPS_TO_PASS
        self._loop_pass_idx = 0

        self._current_bank = 0
        self._midi_channel = 0
        self._note_on_cmd = 0x90
        self._note_off_cmd = 0x80

        self._locked_mode = False  # SHIFT toggles: lock exercises by progress

        self._action_play = False
        self._action_stop = False
        self._action_rec = False
        self._action_select_exercise = -1
        self._action_bank_switch = -1
        self._action_shift_toggle = False

        self._enc_last_pos = None
        self._enc_pressed = False
        self._bpm_adjust_mode = False
        self._action_encoder_delta = 0
        self._action_encoder_push = False

        self._perf_hid_reads = 0
        self._perf_pad_events = 0
        self._perf_midi_sends = 0
        self._perf_led_writes = 0
        self._perf_tick_count = 0
        self._perf_last_print = time.perf_counter()

        self.running = True
        self._led_dirty = False
        self._led_event = threading.Event()
        self._wake_event = threading.Event()
        self._led_thread = threading.Thread(target=self._led_loop, daemon=True)
        self._led_thread.start()

        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    # =====================================================================
    # LED thread
    # =====================================================================

    def _led_loop(self):
        while self.running:
            self._led_event.wait(timeout=0.05)
            self._led_event.clear()
            if self._led_dirty:
                self._led_dirty = False
                self.device.device.write(self.device.led_buffer)
                self._perf_led_writes += 1

    def _signal_led(self):
        self._led_dirty = True
        self._led_event.set()

    def _signal_wake(self):
        self._wake_event.set()

    def _midi_send(self, msg):
        self.midi_out.send_message(msg)

    # =====================================================================
    # Read thread — HID input, pad scoring, MIDI sends
    # =====================================================================

    VEL_THRESHOLD = 50
    HIT_PROTECT_SEC = 0.15   # 150ms: don't overwrite GREEN/YELLOW feedback

    def _read_loop(self):
        hid_dev = self.device.device
        _NOTE_ON = PadEventType.NOTE_ON
        _PRESS_OFF = PadEventType.PRESS_OFF
        _NOTE_OFF = PadEventType.NOTE_OFF
        _PAD_COUNT = PAD_COUNT
        _debug = self.debug
        _vel_thr = self.VEL_THRESHOLD

        while self.running:
            data = hid_dev.read(64, timeout_ms=10)

            if not data:
                continue

            self._perf_hid_reads += 1
            report = data[0]

            if report == 0x01 and len(data) >= 6:
                self._process_buttons(data)

            elif report == 0x02:
                now = time.perf_counter()
                led_changed = False

                for i in range(1, len(data), 3):
                    if i + 2 >= len(data):
                        break

                    pad_idx = data[i]
                    event_byte = data[i + 1]
                    vel_low = data[i + 2]

                    if pad_idx == 0 and event_byte == 0 and vel_low == 0:
                        break
                    if pad_idx >= _PAD_COUNT:
                        continue

                    etype = event_byte & 0xf0
                    vel12 = ((event_byte & 0x0f) << 8) | vel_low
                    vel = min(127, vel12 >> 5)

                    if etype == _NOTE_ON:
                        if vel < _vel_thr:
                            continue

                        self._perf_pad_events += 1
                        self._on_pad_hit(pad_idx, vel, now)
                        led_changed = True

                    elif etype == 0x00 and _debug and vel > 0:
                        layer_idx = self._pad_layer.get(pad_idx)
                        if layer_idx is not None:
                            layer = self.exercise.layers[layer_idx] if self.exercise else None
                            upad = layer.user_pad if layer else pad_idx
                            print(f"  [PRESS_ON] pad {upad} v={vel:3d} (aftertouch, ignored)")

                    elif etype == _PRESS_OFF or etype == _NOTE_OFF:
                        self._on_pad_release(pad_idx)
                        led_changed = True

                if led_changed:
                    self._signal_led()

    # =====================================================================
    # Main thread — state machine + metronome
    # =====================================================================

    def run(self):
        """Main loop: process actions, tick metronome, update screen."""
        self._enter_lesson_select()
        try:
            while self.running:
                self._process_actions()

                # Handle DEMO finished → back to EX_IDLE
                if self._demo_finished:
                    self._demo_finished = False
                    if self.clock:
                        self.clock.stop()
                    self._all_notes_off()
                    self._enter_exercise_idle()

                if self.state == 'EX_COUNTDOWN':
                    self._tick_countdown()
                    time.sleep(0.001)
                elif self.state in ('EX_DEMO', 'EX_PLAYING'):
                    self._tick_metronome()
                    self._perf_tick_count += 1
                    time.sleep(0.001)
                else:
                    self._wake_event.wait(timeout=0.1)
                    self._wake_event.clear()

                # Debug: print perf stats every 3 seconds
                if self.debug:
                    now = time.perf_counter()
                    dt = now - self._perf_last_print
                    if dt >= 3.0:
                        hz = self._perf_tick_count / dt if dt > 0 else 0
                        print(f"  [PERF] {dt:.1f}s: "
                              f"ticks={self._perf_tick_count}({hz:.0f}Hz) "
                              f"hid={self._perf_hid_reads} "
                              f"pads={self._perf_pad_events} "
                              f"midi={self._perf_midi_sends} "
                              f"led={self._perf_led_writes} "
                              f"state={self.state} "
                              f"step={self._last_step}")
                        self._perf_hid_reads = 0
                        self._perf_pad_events = 0
                        self._perf_midi_sends = 0
                        self._perf_led_writes = 0
                        self._perf_tick_count = 0
                        self._perf_last_print = now
        except _ExitSignal:
            pass
        finally:
            self._cleanup()

    def _process_actions(self):
        """Consume action flags set by the read thread."""
        # SHIFT: toggle locked mode (only in LESSON_SELECT)
        if self._action_shift_toggle:
            self._action_shift_toggle = False
            if self.state == 'LESSON_SELECT':
                self._locked_mode = not self._locked_mode
                mode_str = "ON (progress lock)" if self._locked_mode else "OFF (free)"
                print(f"  🔒 Locked mode: {mode_str}")
                self._enter_lesson_select()
            return

        # Bank switch (only in LESSON_SELECT)
        bank = self._action_bank_switch
        if bank >= 0:
            self._action_bank_switch = -1
            if self.state == 'LESSON_SELECT' and bank != self._current_bank:
                self._set_bank(bank)
                self._enter_lesson_select()
            return

        # Exercise selection (from LESSON_SELECT pad press)
        ex_idx = self._action_select_exercise
        if ex_idx >= 0:
            self._action_select_exercise = -1
            if self.state == 'LESSON_SELECT':
                # In locked mode, check if exercise is unlocked
                if self._locked_mode:
                    if not self._is_exercise_unlocked(ex_idx):
                        print(f"  🔒 Exercise locked — complete previous first")
                        return
                self._enter_exercise_idle(ex_idx)
            return

        if self._action_stop:
            self._action_stop = False
            self._bpm_adjust_mode = False
            if self.state == 'EX_IDLE':
                self._enter_lesson_select()
            elif self.state in ('EX_DEMO', 'EX_COUNTDOWN', 'EX_PLAYING'):
                self._enter_exercise_idle()
            return

        if self._action_rec:
            self._action_rec = False
            if self.state == 'EX_IDLE':
                self._bpm_adjust_mode = False
                self._enter_demo()
            return

        # Encoder push: toggle BPM adjust mode in EX_IDLE
        if self._action_encoder_push:
            self._action_encoder_push = False
            if self.state == 'EX_IDLE':
                self._bpm_adjust_mode = not self._bpm_adjust_mode
                if self._bpm_adjust_mode:
                    self._render_bpm_screen()
                else:
                    self.scr.render_pattern(self.exercise)
                    self.scr.write(self.device)

        # Encoder turn: adjust BPM if in adjust mode
        delta = self._action_encoder_delta
        if delta != 0:
            self._action_encoder_delta = 0
            if self.state == 'EX_IDLE' and self._bpm_adjust_mode:
                self._current_bpm = max(self.BPM_MIN,
                                        min(self.BPM_MAX, self._current_bpm + delta))
                self.clock.set_bpm(self._current_bpm)
                self._render_bpm_screen()

        if self._action_play:
            self._action_play = False
            if self.state == 'EX_IDLE':
                self._bpm_adjust_mode = False
                self._enter_countdown()
            elif self.state == 'EX_DEMO':
                if self.clock:
                    self.clock.stop()
                self._all_notes_off()
                self._enter_countdown()
            return

    BPM_STEP = 5
    BPM_MIN = 40
    BPM_MAX = 200

    def _load_exercise(self, ex_idx):
        self.exercise = self.exercises[ex_idx]
        self._current_bpm = self.exercise.bpm
        self.clock = ClockEngine(self._current_bpm, self.exercise.steps,
                                 self.exercise.subdivisions)
        self._pad_layer = {}
        for i, layer in enumerate(self.exercise.layers):
            self._pad_layer[layer.pad_idx] = i
        self._hit_protect = {}
        self._pressed_notes = {}

    # =====================================================================
    # Bank switching
    # =====================================================================

    def _set_bank(self, bank_idx):
        self._current_bank = bank_idx
        self._midi_channel = bank_idx
        self._note_on_cmd = 0x90 + bank_idx
        self._note_off_cmd = 0x80 + bank_idx

    def _update_bank_leds(self):
        for btn_id, _ in BANK_BUTTONS:
            self.rend.button_led_off(btn_id)
        active_btn = BANK_BUTTONS[self._current_bank][0]
        self.rend.button_led(active_btn, Color.WHITE, BRIGHTNESS_BRIGHT)

    def _is_exercise_unlocked(self, ex_idx):
        """Check if exercise is unlocked based on previous progress.
        
        Rules:
        - First exercise in each row (slots 0, 4, 8, 12) is always unlocked
        - Other exercises require previous exercise in row to be green/yellow
        """
        if not self.stats:
            return True
        
        slot_in_bank = ex_idx % EXERCISES_PER_BANK
        # First exercise in each row is always unlocked
        if slot_in_bank % 4 == 0:
            return True
        
        # Check previous exercise in the row
        prev_idx = ex_idx - 1
        progress = self.stats.last_results()
        prev_grade = progress.get(prev_idx)
        
        # Unlocked if previous is green or yellow (passed)
        return prev_grade in ('green', 'yellow')

    # =====================================================================
    # State: LESSON_SELECT — pick exercise by pressing a pad
    # =====================================================================

    def _enter_lesson_select(self):
        self.state = 'LESSON_SELECT'
        if self.clock:
            self.clock.stop()
        self._all_notes_off()
        self.exercise = None
        self._pad_layer = {}

        self.rend.clear_pads()
        self.rend.strip_clear()

        bank = self._current_bank
        base = bank * EXERCISES_PER_BANK
        progress = self.stats.last_results() if self.stats else {}
        _GRADE_COLOR = {'green': Color.GREEN, 'yellow': Color.YELLOW, 'red': Color.RED}

        self._lesson_pad_map = {}
        for slot in range(EXERCISES_PER_BANK):
            ex_idx = base + slot
            if ex_idx >= len(self.exercises):
                break
            pidx = user_to_idx(slot + 1)
            grade = progress.get(ex_idx)
            
            # Check if locked in locked mode
            is_locked = self._locked_mode and not self._is_exercise_unlocked(ex_idx)
            
            if is_locked:
                # Locked: dim red
                color = Color.RED
                brightness = BRIGHTNESS_DIM
            elif grade:
                color = _GRADE_COLOR.get(grade, Color.WHITE)
                brightness = BRIGHTNESS_BRIGHT
            else:
                color = Color.WHITE
                brightness = BRIGHTNESS_DIM
            self.rend.pad(pidx, color, brightness)
            self._lesson_pad_map[pidx] = ex_idx

        self.rend.button_led_off(BTN_PLAY)
        self.rend.button_led_off(BTN_STOP)
        self.rend.button_led_off(BTN_REC)
        # SHIFT LED shows locked mode state
        if self._locked_mode:
            self.rend.button_led(BTN_SHIFT, Color.RED, BRIGHTNESS_BRIGHT)
        else:
            self.rend.button_led_off(BTN_SHIFT)
        self._update_bank_leds()
        self._signal_led()

        self.scr.render_logo()
        self.scr.write(self.device)

        _GRADE_EMOJI = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}
        bank_name = BANK_NAMES[bank] if bank < len(BANK_NAMES) else f"Bank {bank}"
        lock_str = " 🔒" if self._locked_mode else ""
        print(f"\n{'=' * 56}")
        print(f"  {bank_name}  (MIDI ch {self._midi_channel + 1}){lock_str}")
        print(f"{'=' * 56}")
        for slot in range(EXERCISES_PER_BANK):
            ex_idx = base + slot
            if ex_idx >= len(self.exercises):
                break
            ex = self.exercises[ex_idx]
            grade = progress.get(ex_idx)
            is_locked = self._locked_mode and not self._is_exercise_unlocked(ex_idx)
            if is_locked:
                emoji = '🔒'
            else:
                emoji = _GRADE_EMOJI.get(grade, '⬜')
            subs_label = f" [{ex.subdivisions}/beat]" if ex.subdivisions != 4 else ""
            print(f"  pad {slot + 1:2d} = {emoji} {ex.name}{subs_label}")
        if self._locked_mode:
            print(f"\n  SHIFT = toggle lock off")
        else:
            print(f"\n  SHIFT = toggle progress lock")
        print()

    # =====================================================================
    # State: EX_IDLE — exercise loaded, free play, wait for REC/PLAY
    # =====================================================================

    def _enter_exercise_idle(self, ex_idx=None):
        self.state = 'EX_IDLE'

        if ex_idx is not None:
            self._exercise_idx = ex_idx
            self._load_exercise(ex_idx)

        if self.clock:
            self.clock.stop()
        self._all_notes_off()

        self.rend.clear_pads()
        self.rend.strip_clear()

        for layer in self.exercise.layers:
            self.rend.pad(layer.pad_idx, layer.color, BRIGHTNESS_BRIGHT)

        self.rend.button_led(BTN_PLAY, Color.GREEN, BRIGHTNESS_BRIGHT)
        self.rend.button_led(BTN_STOP, Color.RED, BRIGHTNESS_BRIGHT)
        self.rend.button_led(BTN_REC, Color.WHITE, BRIGHTNESS_BRIGHT)
        self._signal_led()

        # Screen — pattern
        self.scr.render_pattern(self.exercise)
        self.scr.write(self.device)

        # Console
        ex = self.exercise
        print(f"\n{'=' * 56}")
        print(f"  {ex.name}")
        print(f"  BPM: {self._current_bpm}  |  {ex.steps} шагов  "
              f"|  {len(ex.layers)} инструментов")
        print(f"{'=' * 56}")
        print()
        print(_print_beat_ruler(ex.steps, ex.subdivisions))
        for layer in ex.layers:
            print(_print_pattern(layer, ex.subdivisions, label_width=22))
        print()
        for layer in ex.layers:
            emoji = _COLOR_EMOJI.get(layer.color, '⬜')
            print(f"    пад {layer.user_pad:2d} = {emoji} {layer.name}"
                  f" (MIDI {layer.midi_note})")
        print()
        print("  REC  → послушать паттерн")
        print("  PLAY → начать упражнение (с отсчётом)")
        print("  STOP → назад к выбору урока")
        print()

    def _render_bpm_screen(self):
        """Show BPM value on screen (encoder adjust mode)."""
        scr = self.scr.screen
        scr.clear()
        draw_text_5x7(scr, 4, 2, "BPM", scale=1)
        draw_text_5x7(scr, 30, 4, str(self._current_bpm), scale=3)
        self.scr.write(self.device)

    # =====================================================================
    # State: EX_DEMO — pattern plays 1 loop, then back to EX_IDLE
    # =====================================================================

    def _enter_demo(self):
        self.state = 'EX_DEMO'
        self._demo_loops_done = 0
        self._last_step = -1
        self._last_loop = 0
        self._pending_offs.clear()
        self._hit_protect.clear()

        self._draw_resting()
        self.rend.button_led(BTN_REC, Color.RED, BRIGHTNESS_BRIGHT)
        self.rend.button_led(BTN_PLAY, Color.GREEN, BRIGHTNESS_BRIGHT)
        self._signal_led()

        self.clock.start()

        print("  🎧 Слушай паттерн... (1 луп)")
        for layer in self.exercise.layers:
            emoji = _COLOR_EMOJI.get(layer.color, '⬜')
            print(f"     {emoji} Пад {layer.user_pad} ({layer.name})")
        print(f"     (PLAY = начать упражнение)\n")

    # =====================================================================
    # State: EX_COUNTDOWN — 4 beats then play
    # =====================================================================

    def _enter_countdown(self):
        self.state = 'EX_COUNTDOWN'
        if self.clock:
            self.clock.stop()
        self._all_notes_off()

        self.tracker.init_pass(len(self.exercise.layers))
        self._pass_base = 0
        self._pass_start_time = time.perf_counter()
        self._last_step = -1
        self._last_loop = -1
        self._pending_offs.clear()
        self._hit_protect.clear()

        self._loop_grades = [None] * LOOPS_TO_PASS
        self._loop_pass_idx = 0

        self.rend.button_led(BTN_PLAY, Color.YELLOW, BRIGHTNESS_BRIGHT)
        self._signal_led()

        beat_dur = 60.0 / self._current_bpm
        self._ci_origin = time.perf_counter()
        self._ci_exercise_origin = self._ci_origin + self.COUNTDOWN_BEATS * beat_dur
        self._ci_beat_dur = beat_dur
        self._ci_beat = -1
        self._ci_flash_off_done = True

        print("  ⏳ Отсчёт...", end='', flush=True)

    def _tick_countdown(self):
        """Non-blocking count-in: called from main loop at ~1 kHz.
        Fires metronome clicks, pad flashes, and transitions to
        EX_PLAYING with zero dead-zone."""
        now = time.perf_counter()

        if now >= self._ci_exercise_origin:
            # Count-in complete — start clock+state with <1 ms precision.
            self._last_step = -1
            self._last_loop = 0
            self._pass_base = 0
            self.clock.start(self._ci_exercise_origin)
            self.state = 'EX_PLAYING'
            self._enter_playing()
            return

        elapsed = now - self._ci_origin
        beat = int(elapsed / self._ci_beat_dur)
        beat_phase = (elapsed - beat * self._ci_beat_dur) / self._ci_beat_dur

        if beat != self._ci_beat:
            self._ci_beat = beat
            self._ci_flash_off_done = False

            for i in range(16):
                self.rend.pad(i, Color.WHITE, BRIGHTNESS_BRIGHT)
            self.rend.strip_playhead(beat / self.COUNTDOWN_BEATS)
            self._signal_led()

            note = METRO_NOTE_ACCENT if beat == 0 else METRO_NOTE_NORMAL
            vel = METRO_VEL_ACCENT if beat == 0 else METRO_VEL_NORMAL
            self._midi_send([MIDI_NOTE_ON_CH10, note, vel])

            print(f" {beat + 1}", end='', flush=True)

        elif not self._ci_flash_off_done and beat_phase > 0.15:
            self._ci_flash_off_done = True
            self.rend.clear_pads()
            for layer in self.exercise.layers:
                self.rend.pad(layer.pad_idx, layer.color, BRIGHTNESS_BRIGHT)
            self._signal_led()
            note = METRO_NOTE_ACCENT if beat == 0 else METRO_NOTE_NORMAL
            self._midi_send([MIDI_NOTE_OFF_CH10, note, 0])

    # =====================================================================
    # State: EX_PLAYING — user plays, metronome + loop meter grading
    # =====================================================================

    def _enter_playing(self):
        # State + clock already set by _tick_countdown with <1 ms precision.
        # Visual setup only (non-time-critical).
        self._draw_resting()
        self._clear_loop_meter()
        self.rend.button_led(BTN_PLAY, Color.GREEN, BRIGHTNESS_BRIGHT)
        self.rend.button_led(BTN_STOP, Color.RED, BRIGHTNESS_BRIGHT)
        self.rend.button_led_off(BTN_REC)
        self._signal_led()

        print("\n  ▶  Играй!")
        for layer in self.exercise.layers:
            emoji = _COLOR_EMOJI.get(layer.color, '⬜')
            print(f"     {emoji} Пад {layer.user_pad} ({layer.name})")
        print(f"     STOP → остановить\n")

    def _tick_metronome(self):
        """Called from main thread ~1kHz. No busy-wait, just check clock."""
        if not self.clock or not self.clock.running:
            return

        step = self.clock.current_step
        loop = self.clock.current_loop

        if loop != self._last_loop:
            self._on_new_loop()
            if self.state not in ('EX_DEMO', 'EX_PLAYING'):
                return
            if self._demo_finished:
                return
            # Re-read: _check_progression may have restarted the clock
            loop = self.clock.current_loop
            step = self.clock.current_step
            self._last_loop = loop

        if step != self._last_step:
            subs = self.exercise.subdivisions
            if self.debug and step % subs == 0:
                elapsed = self.clock.elapsed
                expected = self.clock.step_time(step, loop) - self.clock._origin
                drift = (elapsed - expected) * 1000
                print(f"  [STEP] beat {step//subs + 1}  step={step:2d}  "
                      f"loop={loop}  drift={drift:+.1f}ms")
            self._on_step(step)
            self._process_pending_offs(step, loop)
            self._last_step = step
            self.rend.strip_playhead(step / self.clock.steps)
            self._signal_led()

    # =====================================================================
    # Step events (called from main thread via _tick_metronome)
    # =====================================================================

    def _on_new_loop(self):
        if self.state == 'EX_DEMO':
            self._demo_loops_done += 1
            if self._demo_loops_done >= 1:
                self._demo_finished = True
            return

        if self.state != 'EX_PLAYING':
            return

        self._grade_finished_loop()
        self._check_progression()

    def _grade_finished_loop(self):
        """Grade the loop that just ended and update loop meter."""
        slot = self._loop_pass_idx
        if slot >= LOOPS_TO_PASS:
            return

        overall = 'green'
        ex = self.exercise
        layer_details = []
        for i, layer in enumerate(ex.layers):
            g, reason = self.tracker.grade_loop(
                i, slot, ex.timing_ok_ms, self.HIT_WINDOW_MS,
                expected_hits=layer.hits_per_loop)
            layer_details.append((layer.name, g, reason))
            if g is None or g == 'red':
                overall = 'red'
            elif g == 'yellow' and overall == 'green':
                overall = 'yellow'

        self._loop_grades[slot] = overall

        # Update the meter pad: color the just-finished loop
        pidx = LOOP_METER_PADS[slot]
        if overall == 'green':
            self.rend.pad(pidx, Color.GREEN, BRIGHTNESS_BRIGHT)
        elif overall == 'yellow':
            self.rend.pad(pidx, Color.YELLOW, BRIGHTNESS_BRIGHT)
        else:
            self.rend.pad(pidx, Color.RED, BRIGHTNESS_BRIGHT)

        if self.debug:
            grades_str = ' '.join(
                {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}.get(g, '⚫')
                for g in self._loop_grades
            )
            sym = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}
            detail = ' | '.join(
                f"{n}:{sym.get(g,'⚫')}{reason}"
                for n, g, reason in layer_details
            )
            print(f"  [GRADE] {detail}")
            print(f"  [METER] loop {slot + 1}/{LOOPS_TO_PASS}: {overall}  [{grades_str}]")

        self._loop_pass_idx = slot + 1

        # Show current loop blink on next pad (if within range)
        if self._loop_pass_idx < LOOPS_TO_PASS:
            next_pidx = LOOP_METER_PADS[self._loop_pass_idx]
            self.rend.pad(next_pidx, Color.WHITE, BRIGHTNESS_DIM)

        self._signal_led()

        # Print layer stats every 2 loops
        if self._loop_pass_idx % 2 == 0:
            self._print_layers()

    def _check_progression(self):
        """After 8 loops: show result, adjust BPM, count-in if changed."""
        if self._loop_pass_idx < LOOPS_TO_PASS:
            return

        greens = sum(1 for g in self._loop_grades if g == 'green')
        yellows = sum(1 for g in self._loop_grades if g == 'yellow')
        reds = sum(1 for g in self._loop_grades if g == 'red')
        all_pass = all(g in ('green', 'yellow') for g in self._loop_grades)

        old_bpm = self._current_bpm
        good_enough = greens >= LOOPS_TO_PASS - 2
        if good_enough:
            self._current_bpm = min(self.BPM_MAX,
                                    self._current_bpm + self.BPM_STEP)
        elif reds > 4:
            self._current_bpm = max(self.BPM_MIN,
                                    self._current_bpm - self.BPM_STEP)

        bpm_changed = self._current_bpm != old_bpm

        if good_enough:
            bpm_str = (f"  ⬆ BPM {old_bpm} → {self._current_bpm}"
                       if bpm_changed else "")
            print(f"\n  🎉 Отлично! 🟢{greens}{bpm_str}\n")
        elif reds > 4:
            bpm_str = (f"  ⬇ BPM {old_bpm} → {self._current_bpm}"
                       if bpm_changed else "")
            print(f"\n  ↻ Ещё раз! 🟢{greens} 🟡{yellows} 🔴{reds}{bpm_str}\n")
        else:
            print(f"\n  ➡ Продолжаем BPM {self._current_bpm}  🟢{greens} 🟡{yellows} 🔴{reds}\n")

        if self.stats:
            duration_s = time.perf_counter() - self._pass_start_time
            ex = self.exercise
            loop_layers = []
            for slot in range(LOOPS_TO_PASS):
                layers_info = []
                for li, layer in enumerate(ex.layers):
                    loop_data = self.tracker._loops.get(li, [{}] * LOOPS_TO_PASS)[slot]
                    extras = self.tracker._extras.get(li, [0] * LOOPS_TO_PASS)[slot]
                    hits = len(loop_data)
                    max_off = max((abs(o) for o, _ in loop_data.values()), default=0.0)
                    lg, _ = self.tracker.grade_loop(
                        li, slot, ex.timing_ok_ms, self.HIT_WINDOW_MS,
                        expected_hits=layer.hits_per_loop)
                    layers_info.append({
                        'name': layer.name,
                        'grade': lg,
                        'hits': hits,
                        'expected': layer.hits_per_loop,
                        'extras': extras,
                        'max_off': round(max_off, 1),
                    })
                loop_layers.append(layers_info)

            ex_name = ex.name
            self.stats.write_pass(
                exercise_name=ex_name,
                exercise_idx=self._exercise_idx,
                bpm=old_bpm,
                bpm_after=self._current_bpm,
                subdivisions=ex.subdivisions,
                duration_s=duration_s,
                loop_grades=self._loop_grades,
                loop_layers=loop_layers,
            )

        self._loop_grades = [None] * LOOPS_TO_PASS
        self._loop_pass_idx = 0
        self._clear_loop_meter()

        self.tracker.init_pass(len(self.exercise.layers))
        self._pass_base = self.clock.current_loop if self.clock and self.clock.running else 0
        self._pass_start_time = time.perf_counter()

        if bpm_changed:
            self.clock.set_bpm(self._current_bpm)
            self._enter_countdown()

    def _clear_loop_meter(self):
        """Turn off all loop meter pads and show first one as 'current'."""
        for pidx in LOOP_METER_PADS:
            self.rend.pad(pidx, Color.OFF, 0)
        if LOOPS_TO_PASS > 0:
            self.rend.pad(LOOP_METER_PADS[0], Color.WHITE, BRIGHTNESS_DIM)
        self._signal_led()

    def _on_step(self, step):
        subs = self.exercise.subdivisions
        if step % subs == 0:
            note = METRO_NOTE_ACCENT if step == 0 else METRO_NOTE_NORMAL
            vel = METRO_VEL_ACCENT if step == 0 else METRO_VEL_NORMAL
            self._midi_send([MIDI_NOTE_ON_CH10, note, vel])
            off_step = (step + max(1, subs // 2)) % self.exercise.steps
            off_loop = self.clock.current_loop
            if off_step <= step:
                off_loop += 1
            self._pending_offs.append((off_loop, off_step, note, MIDI_NOTE_OFF_CH10))

        if self.state == 'EX_PLAYING':
            slot = self._loop_pass_idx
            if slot < LOOPS_TO_PASS:
                pidx = LOOP_METER_PADS[slot]
                half = max(1, subs // 2)
                if step % subs == 0:
                    self.rend.pad(pidx, Color.WHITE, BRIGHTNESS_BRIGHT)
                elif step % subs == half:
                    self.rend.pad(pidx, Color.WHITE, BRIGHTNESS_DIM)

        if self.state == 'EX_DEMO':
            self._on_step_demo(step)
        elif self.state == 'EX_PLAYING':
            self._on_step_playing(step)

    def _on_step_demo(self, step):
        """DEMO: flash pads + send MIDI for all layers."""
        midi_batch = []

        for layer in self.exercise.layers:
            pidx = layer.pad_idx

            if layer.hit_at(step):
                self.rend.pad(pidx, Color.WHITE, BRIGHTNESS_BRIGHT)
                note = layer.midi_note
                midi_batch.append([self._note_on_cmd, note, layer.vel_at(step)])
                off_step = (step + self.NOTE_DURATION_STEPS) % self.exercise.steps
                off_loop = self.clock.current_loop
                if off_step <= step:
                    off_loop += 1
                self._pending_offs.append((off_loop, off_step, note, self._note_off_cmd))
            else:
                self.rend.pad(pidx, layer.color, BRIGHTNESS_BRIGHT)

        send = self.midi_out.send_message
        for msg in midi_batch:
            send(msg)
        self._signal_led()

    def _on_step_playing(self, step):
        """PLAYING: visual hints (flash on beat). Respect hit feedback."""
        now = time.perf_counter()
        _hit_prot = self._hit_protect

        for layer in self.exercise.layers:
            pidx = layer.pad_idx

            if pidx in _hit_prot and now < _hit_prot[pidx]:
                continue
            if pidx in _hit_prot:
                del _hit_prot[pidx]

            if layer.hit_at(step):
                self.rend.pad(pidx, Color.WHITE, BRIGHTNESS_BRIGHT)
            else:
                self.rend.pad(pidx, layer.color, BRIGHTNESS_BRIGHT)

        self._signal_led()

    def _process_pending_offs(self, step, loop):
        offs = self._pending_offs
        if not offs:
            return
        batch = []
        i = 0
        while i < len(offs):
            off_loop, off_step, note, status = offs[i]
            if loop > off_loop or (loop == off_loop and step >= off_step):
                batch.append([status, note, 0])
                offs[i] = offs[-1]
                offs.pop()
            else:
                i += 1
        send = self.midi_out.send_message
        for msg in batch:
            send(msg)

    def _all_notes_off(self):
        send = self.midi_out.send_message
        for _, _, note, status in self._pending_offs:
            send([status, note, 0])
        self._pending_offs.clear()
        for note in self._pressed_notes.values():
            send([self._note_off_cmd, note, 0])
        self._pressed_notes.clear()

    # =====================================================================
    # Button handling (from read thread)
    # =====================================================================

    def _process_buttons(self, data):
        for btn_id, action in self._BTN_ACTIONS:
            byte_idx, mask = _BTN_MAP[btn_id]
            pressed = (data[byte_idx] & mask) != 0
            was = self._btn.get(btn_id, False)
            if pressed and not was:
                action()
            self._btn[btn_id] = pressed

        for btn_id, bank_idx in BANK_BUTTONS:
            byte_idx, mask = _BTN_MAP[btn_id]
            pressed = (data[byte_idx] & mask) != 0
            was = self._btn.get(btn_id, False)
            if pressed and not was:
                self._action_bank_switch = bank_idx
                self._signal_wake()
            self._btn[btn_id] = pressed

        # SHIFT: toggle locked mode (only in LESSON_SELECT)
        byte_idx, mask = _BTN_MAP[BTN_SHIFT]
        shift_pressed = (data[byte_idx] & mask) != 0
        shift_was = self._btn.get(BTN_SHIFT, False)
        if shift_pressed and not shift_was:
            self._action_shift_toggle = True
            self._signal_wake()
        self._btn[BTN_SHIFT] = shift_pressed

        if len(data) >= 8:
            self._process_encoder(data)

    def _process_encoder(self, data):
        enc_press = data[5] == 0x80
        enc_touch = data[6] == 0x01
        enc_pos = data[7]

        if enc_press and not self._enc_pressed:
            self._action_encoder_push = True
            self._signal_wake()
        self._enc_pressed = enc_press

        if enc_touch:
            if self._enc_last_pos is not None and enc_pos != self._enc_last_pos:
                delta = enc_pos - self._enc_last_pos
                if delta > 8:
                    delta -= 16
                elif delta < -8:
                    delta += 16
                if delta != 0:
                    self._action_encoder_delta += delta
                    self._signal_wake()
            self._enc_last_pos = enc_pos
        else:
            self._enc_last_pos = None

    def _on_play(self):
        self._action_play = True
        self._signal_wake()

    def _on_stop_btn(self):
        self._action_stop = True
        self._signal_wake()

    def _on_rec(self):
        self._action_rec = True
        self._signal_wake()

    # =====================================================================
    # Pad events (from read thread)
    # =====================================================================

    def _on_pad_hit(self, pad_idx, velocity, hit_time):
        # --- LESSON_SELECT: pad press selects an exercise ---
        if self.state == 'LESSON_SELECT':
            ex_idx = self._lesson_pad_map.get(pad_idx)
            if ex_idx is not None:
                self._action_select_exercise = ex_idx
                self._signal_wake()
            return

        exercise = self.exercise
        if exercise is None:
            return

        layer_idx = self._pad_layer.get(pad_idx)
        if layer_idx is None:
            return

        layer = exercise.layers[layer_idx]
        note = layer.midi_note

        self._midi_send([self._note_on_cmd, note, velocity])
        self._perf_midi_sends += 1
        self._pressed_notes[pad_idx] = note

        # Visual flash (skip loop meter pads)
        if pad_idx not in _LOOP_METER_SET:
            self.rend.pad(pad_idx, Color.WHITE, BRIGHTNESS_BRIGHT)

        # Not in scoring mode: just MIDI + flash
        if self.state != 'EX_PLAYING':
            return

        # --- EX_PLAYING: score the hit ---
        best_step = None
        best_off = float('inf')
        best_loop = None

        clock = self.clock
        loop = clock.current_loop
        loops_to_check = [loop, loop + 1]
        if loop > 0:
            loops_to_check.append(loop - 1)

        for check_loop in loops_to_check:
            for s in layer.hit_steps:
                off = clock.offset_ms(hit_time, s, check_loop)
                if abs(off) < abs(best_off):
                    best_off = off
                    best_step = s
                    best_loop = check_loop

        step = clock.current_step
        if best_step is not None and abs(best_off) < self.HIT_WINDOW_MS:
            slot = best_loop - self._pass_base
            self.tracker.record(layer_idx, slot, best_step, best_off, velocity)
            if best_step == 0 and slot > 0:
                self.tracker.record(layer_idx, slot - 1, 0, best_off, velocity)
            if abs(best_off) < exercise.timing_ok_ms:
                self.rend.pad(pad_idx, Color.GREEN, BRIGHTNESS_BRIGHT)
                grade = "GREEN"
            else:
                self.rend.pad(pad_idx, Color.YELLOW, BRIGHTNESS_BRIGHT)
                grade = "YELLOW"
            self._hit_protect[pad_idx] = hit_time + self.HIT_PROTECT_SEC
            if self.debug:
                tag = " DUP" if best_step == 0 and slot > 0 else ""
                print(f"  [HIT] pad {layer.user_pad} v={velocity:3d}"
                      f"  step={step:2d}  best={best_step:2d}"
                      f"  off={best_off:+6.1f}ms  s{slot} {grade}{tag}")
        else:
            slot = loop - self._pass_base
            self.tracker.record_extra(layer_idx, slot)
            self.rend.pad(pad_idx, Color.RED, BRIGHTNESS_BRIGHT)
            self._hit_protect[pad_idx] = hit_time + self.HIT_PROTECT_SEC
            if self.debug:
                miss_info = (f"best_off={best_off:+.1f}ms"
                             if best_step is not None else "no_hits")
                print(f"  [EXTRA] pad {layer.user_pad} v={velocity:3d}"
                      f"  step={step:2d}  {miss_info}")

    def _on_pad_release(self, pad_idx):
        note = self._pressed_notes.pop(pad_idx, None)
        if note is not None:
            self._midi_send([self._note_off_cmd, note, 0])

        if self.state == 'LESSON_SELECT':
            return
        if pad_idx in _LOOP_METER_SET:
            return
        if pad_idx in self._hit_protect and time.perf_counter() < self._hit_protect[pad_idx]:
            return

        layer_idx = self._pad_layer.get(pad_idx)
        if layer_idx is not None:
            layer = self.exercise.layers[layer_idx]
            self.rend.pad(layer.pad_idx, layer.color, BRIGHTNESS_BRIGHT)
        else:
            self.rend.pad_off(pad_idx)

    # =====================================================================
    # Helpers
    # =====================================================================

    def _draw_resting(self):
        self.rend.clear_pads()
        for layer in self.exercise.layers:
            self.rend.pad(layer.pad_idx, layer.color, BRIGHTNESS_BRIGHT)

    def _print_layers(self):
        grades_str = ' '.join(
            {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}.get(g, '⚫')
            for g in self._loop_grades
        )
        slot = self._loop_pass_idx
        print(f"  [луп {slot}/{LOOPS_TO_PASS}] {grades_str}")

        parts = []
        for i, layer in enumerate(self.exercise.layers):
            sp = self.tracker.spread(i)
            if sp == float('inf'):
                grade = "..."
            elif sp < self.exercise.timing_ok_ms:
                grade = f"✅ {sp:.0f}ms"
            else:
                grade = f"⏳ {sp:.0f}ms"
            parts.append(f"{layer.name}:{grade}")
        print(f"  [{' | '.join(parts)}]")

    def _cleanup(self):
        self.running = False
        if self.clock:
            self.clock.stop()
        self._all_notes_off()

        for t in (self._led_thread, self._read_thread):
            if t.is_alive():
                t.join(timeout=1.0)

        self.rend.clear_pads()
        self.rend.strip_clear()
        self.rend.button_led_off(BTN_PLAY)
        self.rend.button_led_off(BTN_STOP)
        self.rend.button_led_off(BTN_REC)
        self.rend.button_led_off(BTN_SHIFT)
        for btn_id, _ in BANK_BUTTONS:
            self.rend.button_led_off(btn_id)
        try:
            self.device.device.write(self.device.led_buffer)
        except Exception:
            pass
        self.scr.clear(self.device)

        if self.midi_out:
            self.midi_out.close_port()
            self.midi_out = None


class _ExitSignal(Exception):
    pass


# =============================================================================
# Load exercises from JSON
# =============================================================================

EXERCISES_JSON = Path(__file__).parent / "exercises.json"

def _load_exercises():
    with open(EXERCISES_JSON) as f:
        raw = json.load(f)
    return [ex for ex in raw if 'name' in ex]



# =============================================================================
# Main
# =============================================================================

def main():
    args = sys.argv[1:]

    all_exercises = _load_exercises()

    if '--list' in args:
        print("\n  Exercises:\n")
        for i, ex in enumerate(all_exercises):
            n = len(ex['layers'])
            print(f"  {i+1:2d}. {ex['name']}  ({ex['bpm']} BPM, {n} layers)")
        print(f"\nUsage: python3 {sys.argv[0]} [lesson.json]")
        return

    exercise_list = [Exercise(ex) for ex in all_exercises]

    # Load custom JSON exercise if provided
    for a in args:
        if a.startswith('--'):
            continue
        if Path(a).exists() and a.endswith('.json'):
            custom = Exercise.from_json(a)
            exercise_list.append(custom)
            break

    # ---- Device discovery (same flow as midi_bridge_async.py) ----
    setup_mode = '--setup' in args

    print()
    print("=" * 56)
    print("  Pad Trainer")
    print("=" * 56)
    print()

    sorted_devices = setup_devices_with_config(
        max_count=MAX_DEVICES,
        show_numbers=True,
        show_duration=0.5,
    )

    if not sorted_devices:
        print("  Устройства не найдены")
        print("     1. Подключите Maschine Mikro MK3")
        print("     2. killall NIHardwareAgent")
        return

    devices = []
    config = {}
    for device, device_num in sorted_devices:
        devices.append(device)
        config[device.serial] = device_num

    print(f"  Найдено: {len(devices)} устройств")
    for device, device_num in sorted_devices:
        print(f"     Device {device_num}: {device.serial}")
    print()

    if display_logo_on_devices(devices, LOGO_PATH, 110):
        print(f"  Логотип отображён на {len(devices)} устройствах")
    print()

    if setup_mode:
        new_config = setup_device_mapping_interactive(devices, MAX_DEVICES)
        if not new_config:
            print("  Настройка не завершена")
            for d in devices:
                d.close()
            return
        if save_device_config(new_config):
            config = new_config

    device = sorted_devices[0][0]
    device.device.set_nonblocking(False)

    print("  Controls:")
    print("    PAD MODE / KEYBOARD / CHORDS / STEP — switch bank")
    print("    REC      — demo (listen to pattern)")
    print("    PLAY     — start exercise")
    print("    STOP     — back")
    print("    SHIFT    — toggle progress lock (unlock by completing prev)")
    print("    ENCODER  — push to adjust BPM")
    print("    Ctrl+C   — quit")
    print()
    print(f"  {len(exercise_list)} exercises in {len(BANK_NAMES)} banks:")
    for i, name in enumerate(BANK_NAMES):
        base = i * EXERCISES_PER_BANK
        n = min(EXERCISES_PER_BANK, len(exercise_list) - base)
        if n > 0:
            ch = i + 1
            print(f"    {name:15s}  {n:2d} exercises  →  MIDI ch {ch}")
    print()

    debug = '--debug' in args

    student_name = None
    for i, a in enumerate(args):
        if a == '--student' and i + 1 < len(args):
            student_name = args[i + 1]
            break

    stats = StatsWriter(student_name) if student_name else None

    trainer = Trainer(device, exercise_list, debug=debug, stats=stats)
    if debug:
        print("  DEBUG mode ON")
    if stats:
        print(f"  Student: {student_name} (session {stats.session})")
        print(f"  Stats: {stats.path}")
    print(f"  MIDI: '{MIDI_PORT_NAME}'")
    print(f"     (подключи в DAW к drum rack)")
    print()

    def on_sig(sig, frame):
        raise _ExitSignal()

    signal.signal(signal.SIGINT, on_sig)
    signal.signal(signal.SIGTERM, on_sig)

    try:
        trainer.run()
    except _ExitSignal:
        pass
    finally:
        for d in devices:
            d.close()
        print("\n  Done\n")


if __name__ == "__main__":
    main()
