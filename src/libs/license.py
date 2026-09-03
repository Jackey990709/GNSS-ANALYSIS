"""客户端离线 License 校验。仅包含公钥，绝不包含签发私钥。"""

from __future__ import annotations

import base64
import binascii
import ctypes
import hashlib
import hmac
import json
import os
import ssl
import tempfile
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.util.gen_info import DeviceInfoError, collect_device_info
from dotenv import load_dotenv

load_dotenv()  # 从 .env 文件加载环境变量

LICENSE_FORMAT = "GNSSAnalysis-License"
ACTIVATION_RECEIPT_FORMAT = "GNSSAnalysis-Activation-Receipt"
ALGORITHM = "Ed25519"
SCHEMA_VERSION = 1
PRODUCT = "GNSSAnalysis"
MAX_LICENSE_SIZE = 64 * 1024
REQUIRED_FEATURES = frozenset({"position", "pps", "report"})
ROLLBACK_TOLERANCE = timedelta(minutes=5)
ACTIVATION_TIME_TOLERANCE = timedelta(minutes=10)
NETWORK_TIME_URLS = (
    "https://cn.bing.com/",
    "https://beijingshijian.net/",
    "https://www.microsoft.com",
)
ACTIVATION_URL_ENV = "GNSS_ANALYSIS_ACTIVATION_URL"
_STATE_VERSION = 1

# 签发端 tools/license-signing.public.pem 的公开验证密钥；可以随客户端发布。
_PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAIbLYgayfWmwYfDGZy3zCc9fiOPcpBq3ltW5oq2aygA4=
-----END PUBLIC KEY-----
"""
TRUSTED_PUBLIC_KEYS = {
    "gnss-license-signing-2026-01-auto": _PUBLIC_KEY_PEM,
}


class LicenseValidationError(ValueError):
    """表示 License 文件无效、过期或不属于当前计算机。"""


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _bytes_to_blob(value: bytes) -> tuple[_DataBlob, Any]:
    buffer = ctypes.create_string_buffer(value)
    return (
        _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))),
        buffer,
    )


def _dpapi_protect(value: bytes) -> bytes:
    """使用当前 Windows 用户的 DPAPI 加密状态数据。"""
    if os.name != "nt":
        raise LicenseValidationError("License state protection requires Windows")
    source, source_buffer = _bytes_to_blob(value)
    result = _DataBlob()
    crypt_protect = ctypes.windll.crypt32.CryptProtectData
    crypt_protect.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt_protect.restype = wintypes.BOOL
    if not crypt_protect(
        ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(result)
    ):
        raise LicenseValidationError("Unable to protect license state")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)


def _dpapi_unprotect(value: bytes) -> bytes:
    """解密当前 Windows 用户的 DPAPI 状态数据。"""
    if os.name != "nt":
        raise LicenseValidationError("License state protection requires Windows")
    source, source_buffer = _bytes_to_blob(value)
    result = _DataBlob()
    crypt_unprotect = ctypes.windll.crypt32.CryptUnprotectData
    crypt_unprotect.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt_unprotect.restype = wintypes.BOOL
    if not crypt_unprotect(
        ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(result)
    ):
        raise LicenseValidationError("Unable to decrypt license state")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)


def _device_key(device_info: str) -> bytes:
    return hashlib.sha256(
        f"gnss-last-seen:{device_info.lower()}".encode("ascii")
    ).digest()


def _state_locations() -> tuple[tuple[str, Any], ...]:
    """返回当前用户可写入的分散授权状态位置。"""
    app_data = Path(os.environ.get("APPDATA", "."))
    local_app_data = Path(os.environ.get("LOCALAPPDATA", "."))

    return (
        ("file", local_app_data / PRODUCT / "application-state.dat"),
        ("registry", ("HKCU", rf"Software\{PRODUCT}\State", "Data")),
        ("file", app_data / PRODUCT / "application-state.dat"),
        ("registry", ("HKCU", rf"Software\{PRODUCT}\Cache", "Data")),
    )


def _read_location(location: tuple[str, Any]) -> bytes | None:
    kind, target = location
    if kind == "file":
        try:
            return Path(target).read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise LicenseValidationError("Unable to read license state") from exc

    import winreg

    hive_name, key_path, value_name = target
    hive = (
        winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    )
    try:
        with winreg.OpenKey(hive, key_path) as key:
            value, value_type = winreg.QueryValueEx(key, value_name)
        if value_type != winreg.REG_BINARY or not isinstance(value, bytes):
            raise LicenseValidationError("License state is invalid")
        return value
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LicenseValidationError("Unable to read license state") from exc


def _write_location(location: tuple[str, Any], value: bytes) -> None:
    kind, target = location
    if kind == "file":
        path = Path(target)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
                file.write(value)
                temporary_path = Path(file.name)
            os.replace(temporary_path, path)
        except OSError as exc:
            raise LicenseValidationError("Unable to write license state") from exc
        return

    import winreg

    hive_name, key_path, value_name = target
    hive = (
        winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    )
    try:
        with winreg.CreateKeyEx(hive, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_BINARY, value)
    except OSError as exc:
        raise LicenseValidationError("Unable to write license state") from exc


def _encode_state(last_seen: datetime, device_info: str) -> bytes:
    timestamp = last_seen.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mac = hmac.new(
        _device_key(device_info), timestamp.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return json.dumps(
        {"v": _STATE_VERSION, "t": timestamp, "m": mac}, separators=(",", ":")
    ).encode("ascii")


def _decode_state(value: bytes, device_info: str) -> datetime:
    try:
        document = _strict_json_loads(_dpapi_unprotect(value))
        if not isinstance(document, dict) or set(document) != {"v", "t", "m"}:
            raise ValueError
        timestamp, mac = document["t"], document["m"]
        if document["v"] != _STATE_VERSION or not isinstance(mac, str):
            raise ValueError
        expected = hmac.new(
            _device_key(device_info), timestamp.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(mac, expected):
            raise ValueError
        return _parse_utc_timestamp(timestamp, "state timestamp")
    except (
        AttributeError,
        TypeError,
        ValueError,
        UnicodeEncodeError,
        LicenseValidationError,
    ) as exc:
        raise LicenseValidationError("License state has been modified") from exc


def _read_last_seen(device_info: str) -> datetime | None:
    """读取所有副本；已激活设备缺少任意副本即拒绝。"""
    values = [_read_location(location) for location in _state_locations()]
    present = [value for value in values if value is not None]
    if not present:
        return None
    return max(_decode_state(value, device_info) for value in present)


def _write_last_seen(last_seen: datetime, device_info: str) -> None:
    protected = _dpapi_protect(_encode_state(last_seen, device_info))
    for location in _state_locations():
        _write_location(location, protected)


def _fetch_network_time() -> datetime | None:
    """尝试从 HTTPS Date 响应头对时；优先北京时间，失败回退微软；任何网络问题均静默回退。"""
    for url in NETWORK_TIME_URLS:
        try:
            request = Request(url, method="HEAD")
            with urlopen(request, timeout=3) as response:
                date_header = response.headers.get("Date")
            if not date_header:
                continue
            return parsedate_to_datetime(date_header).astimezone(timezone.utc)
        except (OSError, URLError, ValueError) as exc:
            print(f"Failed to fetch network time from {url}: {exc}")
            continue
    return None


def _http_error_detail(exc: HTTPError) -> str:
    """从 HTTPError 响应体中提取 FastAPI 的 detail 文本；失败时按状态码给兜底文案。"""
    try:
        body = json.loads(exc.read().decode("utf-8"))
        if isinstance(body, dict) and isinstance(body.get("detail"), str):
            return body["detail"]
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        pass
    fallbacks = {
        400: "License is invalid or does not match this device",
        409: "Activation record requires administrator recovery",
        410: "License has expired",
        425: "License is not yet active",
        503: "Activation service is unavailable, please retry later",
    }
    return fallbacks.get(exc.code, "First-run online activation was rejected")


def _activate_first_run(
    envelope: Mapping[str, Any],
    device_info: str,
    ref_time: datetime,
) -> datetime:
    """通过发行方激活服务及其签名回执初始化本地授权状态。

    返回服务端返回的权威 last_seen（服务器系统时间）。
    """
    server_host = os.environ.get("SERVER_HOST", "")
    server_port = os.environ.get("SERVER_PORT", "")

    if not server_host or not server_port:
        raise LicenseValidationError(
            "Activation server host and port must be configured"
        )

    activation_url = f"https://{server_host}:{server_port}/activate"
    print(f"Activating license with server at {activation_url}...")
    ca_file = Path(os.getcwd()) / "certs" / "fullchain.pem"
    try:
        ssl_context = ssl.create_default_context(cafile=ca_file)
    except (OSError, ssl.SSLError) as exc:
        raise LicenseValidationError("Activation CA certificate is invalid") from exc
    request_body = json.dumps(
        {"product": PRODUCT, "device_info": device_info, "license": dict(envelope)},
        separators=(",", ":"),
    ).encode("utf-8")
    try:
        request = Request(
            activation_url,
            request_body,
            {"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=3, context=ssl_context) as response:
            response_data = json.loads(response.read().decode("utf-8"))
        if (
            not isinstance(response_data, dict)
            or response_data.get("activated") is not True
            or not isinstance(response_data.get("receipt"), dict)
        ):
            raise ValueError
        _validate_activation_receipt(
            response_data["receipt"], envelope, device_info, ref_time
        )
        server_last_seen = _parse_utc_timestamp(
            response_data.get("last_seen"), "activation last_seen"
        )
    except LicenseValidationError:
        raise
    except (
        OSError,
        URLError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        if isinstance(exc, HTTPError):
            raise LicenseValidationError(_http_error_detail(exc)) from exc
        if "urlopen error" in str(exc):
            raise LicenseValidationError(
                "Please connect to the Internet for first-run activation"
            ) from exc
        raise LicenseValidationError(
            "First-run online activation was rejected"
        ) from exc
    local_time = datetime.now(timezone.utc)
    if abs(local_time - server_last_seen) > ACTIVATION_TIME_TOLERANCE:
        raise LicenseValidationError("Local clock deviates too far from server time")
    _write_last_seen(server_last_seen, device_info)
    return server_last_seen


def _validate_activation_receipt(
    receipt: Mapping[str, Any],
    license_envelope: Mapping[str, Any],
    device_info: str,
    ref_time: datetime,
) -> None:
    expected_fields = {"format", "algorithm", "key_id", "payload", "signature"}
    if set(receipt) != expected_fields:
        raise LicenseValidationError("Activation receipt fields are invalid")
    if (
        receipt.get("format") != ACTIVATION_RECEIPT_FORMAT
        or receipt.get("algorithm") != ALGORITHM
    ):
        raise LicenseValidationError("Activation receipt format is invalid")

    key_id = receipt.get("key_id")
    payload_text = receipt.get("payload")
    signature_text = receipt.get("signature")
    if (
        not isinstance(key_id, str)
        or not isinstance(payload_text, str)
        or not isinstance(signature_text, str)
    ):
        raise LicenseValidationError("Activation receipt values are invalid")
    try:
        receipt_bytes = base64.b64decode(payload_text, validate=True)
        signature = base64.b64decode(signature_text, validate=True)
        _load_public_key(key_id).verify(signature, receipt_bytes)
    except (binascii.Error, ValueError, InvalidSignature) as exc:
        raise LicenseValidationError("Activation receipt signature is invalid") from exc

    receipt_payload = _strict_json_loads(receipt_bytes)
    if not isinstance(receipt_payload, dict) or set(receipt_payload) != {
        "v",
        "product",
        "device_info",
        "license_digest",
        "activated_at",
    }:
        raise LicenseValidationError("Activation receipt payload is invalid")
    license_payload = license_envelope.get("payload")
    if not isinstance(license_payload, str):
        raise LicenseValidationError("License envelope is invalid")
    try:
        digest = hashlib.sha256(
            base64.b64decode(license_payload, validate=True)
        ).hexdigest()
    except (binascii.Error, ValueError) as exc:
        raise LicenseValidationError("License envelope is invalid") from exc
    if (
        receipt_payload.get("v") != 1
        or receipt_payload.get("product") != PRODUCT
        or receipt_payload.get("device_info") != device_info.lower()
        or receipt_payload.get("license_digest") != digest
    ):
        raise LicenseValidationError("Activation receipt does not match license")
    _parse_utc_timestamp(receipt_payload.get("activated_at"), "receipt timestamp")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LicenseValidationError("License JSON contains duplicate keys")
        result[key] = value
    return result


def _strict_json_loads(data: bytes) -> Any:
    try:
        return json.loads(
            data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LicenseValidationError("License JSON is invalid") from exc


def _parse_utc_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise LicenseValidationError(f"License {field} is invalid")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise LicenseValidationError(f"License {field} is invalid") from exc


def _load_public_key(key_id: str) -> Ed25519PublicKey:
    pem = TRUSTED_PUBLIC_KEYS.get(key_id)
    if pem is None:
        raise LicenseValidationError("License signing key is not trusted")
    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, Ed25519PublicKey):
        raise LicenseValidationError("License signing key is invalid")
    return key


class LicenseValidator:
    """验证签名、产品、有效期、全部功能和设备绑定。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def validate(self) -> dict[str, Any]:
        envelope = self._read_envelope()
        payload = self._verify_envelope(envelope)
        self._validate_payload(payload, envelope)
        return payload

    def _read_envelope(self) -> Mapping[str, Any]:
        try:
            content = self.path.read_bytes()
        except OSError as exc:
            raise LicenseValidationError("License file cannot be read") from exc
        if not content or len(content) > MAX_LICENSE_SIZE:
            raise LicenseValidationError("License file size is invalid")
        envelope = _strict_json_loads(content)
        if not isinstance(envelope, dict):
            raise LicenseValidationError("License envelope is invalid")
        return envelope

    @staticmethod
    def _verify_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
        expected_fields = {"format", "algorithm", "key_id", "payload", "signature"}
        if set(envelope) != expected_fields:
            raise LicenseValidationError("License envelope fields are invalid")
        if (
            envelope.get("format") != LICENSE_FORMAT
            or envelope.get("algorithm") != ALGORITHM
        ):
            raise LicenseValidationError("License format is invalid")

        key_id = envelope.get("key_id")
        payload_text = envelope.get("payload")
        signature_text = envelope.get("signature")
        if not all(
            isinstance(value, str) for value in (key_id, payload_text, signature_text)
        ):
            raise LicenseValidationError("License envelope values are invalid")

        try:
            payload_bytes = base64.b64decode(payload_text, validate=True)  # type: ignore
            signature = base64.b64decode(signature_text, validate=True)  # type: ignore
        except (binascii.Error, ValueError) as exc:
            raise LicenseValidationError("License encoding is invalid") from exc
        if not payload_bytes or len(payload_bytes) > MAX_LICENSE_SIZE:
            raise LicenseValidationError("License payload size is invalid")

        try:
            _load_public_key(key_id).verify(signature, payload_bytes)  # type: ignore
        except InvalidSignature as exc:
            raise LicenseValidationError("License signature is invalid") from exc

        payload = _strict_json_loads(payload_bytes)
        if not isinstance(payload, dict):
            raise LicenseValidationError("License payload is invalid")
        return payload

    @staticmethod
    def _device_info(payload: Mapping[str, Any]) -> str:
        # 兼容早期 License 的 machine.components.device_info 格式。
        value = payload.get("device_info")
        if isinstance(value, str):
            return value.lower()
        machine = payload.get("machine")
        if isinstance(machine, dict):
            components = machine.get("components")
            if isinstance(components, dict) and isinstance(
                components.get("device_info"), str
            ):
                return components["device_info"].lower()
        raise LicenseValidationError("License device binding is invalid")

    def _validate_payload(
        self, payload: Mapping[str, Any], envelope: Mapping[str, Any]
    ) -> None:
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise LicenseValidationError("License schema is not supported")
        if payload.get("product") != PRODUCT:
            raise LicenseValidationError("License product does not match")

        not_before = _parse_utc_timestamp(payload.get("not_before"), "not_before")
        expires_at = _parse_utc_timestamp(payload.get("expires_at"), "expires_at")

        features = payload.get("features")
        if not isinstance(features, list) or not all(
            isinstance(item, str) for item in features
        ):
            raise LicenseValidationError("License features are invalid")
        if not REQUIRED_FEATURES.issubset(features):
            raise LicenseValidationError(
                "License does not authorize all application features"
            )

        try:
            device_info = collect_device_info()
        except DeviceInfoError as exc:
            raise LicenseValidationError("Unable to read device information") from exc
        if self._device_info(payload) != device_info.lower():
            raise LicenseValidationError("License is not valid for this computer")

        local_time = datetime.now(timezone.utc)
        network_time = _fetch_network_time()
        ref_time = max(local_time, network_time) if network_time else local_time

        if ref_time < not_before or ref_time >= expires_at:
            raise LicenseValidationError("License is expired")

        last_seen = _read_last_seen(device_info)
        if last_seen is None:
            _activate_first_run(envelope, device_info, ref_time)
            return
        if ref_time + ROLLBACK_TOLERANCE < last_seen:
            raise LicenseValidationError("System time rollback detected")

        _write_last_seen(max(last_seen, ref_time), device_info)
