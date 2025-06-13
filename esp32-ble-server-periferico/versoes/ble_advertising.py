# ble_advertising.py - VERSÃO MODIFICADA

import struct
import bluetooth

# ... (constantes _ADV_TYPE_... permanecem as mesmas) ...
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID128_COMPLETE = const(0x07)


def advertising_payload(limited_discoverable=False, br_edr=False, name=None, services=None, is_scan_response=False):
    payload = bytearray()

    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack("BB", len(value) + 1, adv_type) + value

    # ---- ALTERAÇÃO AQUI ----
    # Adiciona os flags SOMENTE se não for um pacote de scan response
    if not is_scan_response:
        _append(
            _ADV_TYPE_FLAGS,
            struct.pack("B", (0x01 if limited_discoverable else 0x02) + (0x18 if br_edr else 0x04)),
        )

    if name:
        _append(_ADV_TYPE_NAME, name.encode())

    if services:
        for uuid in services:
            b = bytes(uuid)
            # Apenas um exemplo simplificado para UUID de 128 bits
            if len(b) == 16:
                _append(_ADV_TYPE_UUID128_COMPLETE, b)

    return payload