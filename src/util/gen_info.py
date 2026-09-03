"""GNSSAnalysis 客户端设备信息采集模块。

采集稳定硬件标识并生成与签发端 `tools/license_tool.py` 兼容的机器申请文件。

- 设备组件：
    - 采集 machine_guid、smbios_uuid、system_volume 三个稳定字段
    - 每个字段独立规范化并计算 SHA-256 哈希，再按固定顺序合成为 device_info
- 申请文件格式（与签发端一致）：
    {"format": "GNSSAnalysis-License-Request", "schema_version": 1,
     "device_info": "<sha256>"}
- 只输出规范化哈希，不输出原始硬件值。
- 采集方式（均无 wmic / 无命令注入）：
    - machine_guid: 注册表 HKLM\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid
    - smbios_uuid: GetSystemFirmwareTable 读取 SMBIOS Type 1 UUID
    - system_volume: GetVolumeInformationW 读取系统盘卷序列号
- 可直接运行：`python -m tools.gen_device_info`，在当前目录生成 `machine-request.json`
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import subprocess
import sys
import unicodedata
import uuid
from ctypes import wintypes
from pathlib import Path
from typing import Optional

COMPONENT_NAMES = ("machine_guid", "smbios_uuid", "system_volume")
DEVICE_INFO_NAME = "device_info"
REQUEST_FORMAT = "GNSSAnalysis-License-Request"
SCHEMA_VERSION = 1

_INVALID_VALUES = frozenset(
    {
        "",
        "NONE",
        "UNKNOWN",
        "DEFAULT STRING",
        "TO BE FILLED BY O.E.M.",
        "FFFFFFFF",
        "0",
    }
)
_SMBIOS_UUID_INVALID_VALUES = frozenset(
    {
        uuid.UUID(int=0),
        uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
    }
)


class DeviceInfoError(ValueError):
    """Raised when machine component collection fails."""


def normalize_component(value: str) -> str:
    """NFKC 规范化、去空白、统一大写，并剔除无效占位符。"""
    normalized = unicodedata.normalize("NFKC", str(value)).strip().upper()
    if normalized in _INVALID_VALUES:
        raise DeviceInfoError("invalid fingerprint component")
    return normalized


def _get_machine_guid() -> Optional[str]:
    """读取注册表 MachineGuid。"""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value).strip()
    except OSError:
        return None


def _valid_smbios_uuid(raw_uuid: bytes) -> Optional[str]:
    """将 SMBIOS Type 1 UUID 转为字符串，并拒绝保留值。"""
    if len(raw_uuid) != 16:
        return None
    try:
        # SMBIOS 2.6+ 的前三个 UUID 字段按小端序保存。
        value = uuid.UUID(bytes_le=raw_uuid)
    except ValueError:
        return None
    if value in _SMBIOS_UUID_INVALID_VALUES:
        return None
    return str(value)


def _get_smbios_uuid_from_firmware_table() -> Optional[str]:
    """从原始 SMBIOS Type 1 系统信息记录读取 UUID。"""
    try:
        get_table = ctypes.windll.kernel32.GetSystemFirmwareTable
        get_table.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        get_table.restype = wintypes.UINT

        provider = int.from_bytes(b"RSMB", "little")
        size = get_table(provider, 0, None, 0)
        if size < 8:
            return None
        buffer = ctypes.create_string_buffer(size)
        written = get_table(provider, 0, buffer, size)
        if written < 8 or written > size:
            return None

        raw = buffer.raw[:written]
        table_length = int.from_bytes(raw[4:8], "little")
        table = raw[8 : 8 + table_length]
        if len(table) != table_length:
            return None

        offset = 0
        while offset + 4 <= len(table):
            record_type = table[offset]
            record_length = table[offset + 1]
            if record_length < 4 or offset + record_length > len(table):
                return None
            if record_type == 1 and record_length >= 24:
                raw_uuid = table[offset + 8 : offset + 24]
                value = _valid_smbios_uuid(raw_uuid)
                if value is not None:
                    return value

            strings_start = offset + record_length
            strings_end = table.find(b"\x00\x00", strings_start)
            if strings_end < 0:
                return None
            offset = strings_end + 2
    except (AttributeError, OSError, ValueError):
        return None
    return None


def _get_smbios_uuid_from_cim() -> Optional[str]:
    """使用 CIM 查询 SMBIOS UUID，作为固件表读取失败时的兼容回退。"""
    command = "(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID"
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None
    try:
        # CIM 返回的是标准文本 UUID，先转换成 SMBIOS 字节再由统一校验处理。
        value = uuid.UUID(result.stdout.strip())
    except ValueError:
        return None
    return _valid_smbios_uuid(value.bytes_le)


def _get_smbios_uuid() -> Optional[str]:
    """优先读取原始 SMBIOS 表，失败时使用 CIM 兼容回退。"""
    return _get_smbios_uuid_from_firmware_table() or _get_smbios_uuid_from_cim()


def _get_system_volume_serial() -> Optional[str]:
    """读取系统盘卷序列号（GetVolumeInformationW）。"""
    try:
        GetVolumeInformationW = ctypes.windll.kernel32.GetVolumeInformationW
        GetVolumeInformationW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPDWORD,
            wintypes.LPDWORD,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        GetVolumeInformationW.restype = wintypes.BOOL

        root = _system_root()
        if not root:
            return None

        volume_name = ctypes.create_unicode_buffer(261)
        file_system = ctypes.create_unicode_buffer(261)
        serial = wintypes.DWORD(0)
        max_component = wintypes.DWORD(0)
        flags = wintypes.DWORD(0)

        ok = GetVolumeInformationW(
            root,
            volume_name,
            len(volume_name),
            ctypes.byref(serial),
            ctypes.byref(max_component),
            ctypes.byref(flags),
            file_system,
            len(file_system),
        )
        if ok:
            return f"{serial.value:08X}"
    except (OSError, AttributeError):
        pass
    return None


def _system_root() -> Optional[str]:
    """返回系统盘根路径，如 'C:\\\\'。"""
    try:
        GetSystemWindowsDirectoryW = ctypes.windll.kernel32.GetSystemWindowsDirectoryW
        GetSystemWindowsDirectoryW.argtypes = [wintypes.LPWSTR, wintypes.UINT]
        GetSystemWindowsDirectoryW.restype = wintypes.UINT
        buf = ctypes.create_unicode_buffer(261)
        n = GetSystemWindowsDirectoryW(buf, len(buf))
        if n:
            windows_dir = buf.value  # 形如 C:\\Windows
            drive = windows_dir[:2]  # "C:"
            return drive + "\\"
    except (OSError, AttributeError):
        pass
    return None


def _hash_component(name: str, value: str) -> str:
    normalized = normalize_component(value)
    source = f"GNSSAnalysis:v1:{name}:{normalized}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def collect_device_info() -> str:
    """采集三项组件并生成合并的 device_info；任一缺失或无效都拒绝。"""
    machine_guid = _get_machine_guid()
    smbios_uuid = _get_smbios_uuid()
    system_volume = _get_system_volume_serial()
    values = {
        "machine_guid": machine_guid,
        "smbios_uuid": smbios_uuid,
        "system_volume": system_volume,
    }
    missing = [name for name in COMPONENT_NAMES if not values[name]]
    if missing:
        raise DeviceInfoError(
            "all machine components are required; missing: " + ", ".join(missing)
        )

    component_hashes = {
        name: _hash_component(name, str(values[name])) for name in COMPONENT_NAMES
    }
    source = "|".join(component_hashes[name] for name in COMPONENT_NAMES).encode(
        "ascii"
    )
    return hashlib.sha256(
        f"GNSSAnalysis:v1:{DEVICE_INFO_NAME}:".encode("ascii") + source
    ).hexdigest()


def generate_application_request() -> dict:
    """生成 GNSSAnalysis-License-Request 申请文件内容。"""
    return {
        "format": REQUEST_FORMAT,
        "schema_version": SCHEMA_VERSION,
        DEVICE_INFO_NAME: collect_device_info(),
    }


def write_application_request(path: str | Path) -> Path:
    """将申请文件写入指定路径（JSON），返回路径。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    document = generate_application_request()
    target.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def main() -> int:
    """生成固定名称的机器申请文件。"""
    try:
        document = generate_application_request()
    except DeviceInfoError as exc:
        print(f"Failed to collect machine components: {exc}", file=sys.stderr)
        return 2

    output = Path("machine-request.json")
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Application request written to {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
