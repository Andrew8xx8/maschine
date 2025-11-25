"""
Device Configuration Management
================================

Модуль для управления конфигурацией порядка устройств.
Конфигурация сохраняется в ~/.maschine_device_config.json
"""

import json
from pathlib import Path
from typing import Dict, Optional, List

# Config file location
CONFIG_FILE = Path.home() / '.maschine_device_config.json'


def load_device_config() -> Dict[str, int]:
    """
    Загрузить конфигурацию устройств

    Returns:
        Dict[serial_number: str, device_number: int]
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_device_config(config: Dict[str, int]) -> bool:
    """
    Сохранить конфигурацию устройств

    Args:
        config: Dict[serial_number: str, device_number: int]

    Returns:
        True if successful
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def sort_devices_by_config(devices, config: Optional[Dict[str, int]] = None):
    """
    Отсортировать устройства согласно конфигурации

    Args:
        devices: List of MaschineDevice
        config: Optional config dict, если None - загрузится автоматически

    Returns:
        List of (device, device_num) sorted by device_num
        Устройства без конфигурации идут в конце в порядке обнаружения
    """
    if config is None:
        config = load_device_config()

    if not config:
        # No config, return devices in discovery order with sequential numbers
        return [(dev, i + 1) for i, dev in enumerate(devices)]

    # Sort devices by config
    configured = []
    unconfigured = []

    for device in devices:
        device_num = config.get(device.serial)
        if device_num:
            configured.append((device, device_num))
        else:
            unconfigured.append(device)

    # Sort configured by device number
    configured.sort(key=lambda x: x[1])

    # Add unconfigured at the end with next available numbers
    used_nums = {num for _, num in configured}
    next_num = max(used_nums) + 1 if used_nums else 1

    for device in unconfigured:
        while next_num in used_nums:
            next_num += 1
        configured.append((device, next_num))
        next_num += 1

    return configured


def get_config_path() -> Path:
    """Получить путь к файлу конфигурации"""
    return CONFIG_FILE


def has_config() -> bool:
    """Проверить существует ли конфигурация"""
    return CONFIG_FILE.exists()

