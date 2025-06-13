"""
Constantes BLE otimizadas para ESP32
Centraliza todas as definições para economia de memória
"""

import bluetooth
from micropython import const

# Eventos BLE
IRQ_CENTRAL_CONNECT = const(1)
IRQ_CENTRAL_DISCONNECT = const(2)
IRQ_GATTS_WRITE = const(3)
IRQ_SCAN_RESULT = const(5)
IRQ_SCAN_DONE = const(6)
IRQ_PERIPHERAL_CONNECT = const(7)
IRQ_PERIPHERAL_DISCONNECT = const(8)
IRQ_GATTC_SERVICE_RESULT = const(9)
IRQ_GATTC_SERVICE_DONE = const(10)
IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
IRQ_GATTC_DESCRIPTOR_DONE = const(14)
IRQ_GATTC_READ_RESULT = const(15)
IRQ_GATTC_READ_DONE = const(16)
IRQ_GATTC_WRITE_DONE = const(17)
IRQ_GATTC_NOTIFY = const(18)

# UUIDs específicos                   
SENSOR_SERVICE_UUID = bluetooth.UUID("6E400000-B5A3-F393-E0A9-E50E24DCCA9E")
ANALOG_VALUE_CHAR_UUID = bluetooth.UUID("6E400000-B5A3-F393-E0A9-E50E24DCCA9E")
CCCD_UUID = bluetooth.UUID(0x2902)
NOTIFY_ENABLE = const(1)

# Estados da máquina
STATE_IDLE = const(0)
STATE_SCANNING = const(1)
STATE_CONNECTING = const(2)
STATE_CONNECTED = const(3)
STATE_DISCOVERING = const(4)
STATE_READY = const(5)
STATE_ERROR = const(6)
STATE_RECONNECTING = const(7)

STATE_NAMES = ["IDLE", "SCANNING", "CONNECTING", "CONNECTED", 
               "DISCOVERING", "READY", "ERROR", "RECONNECTING"]

# Configuração padrão ESP32
DEFAULT_CONFIG = {
    'scan_duration': 25000,
    'connection_timeout': 8000,
    'discovery_timeout': 6000,
    'read_timeout': 4000,
    'max_retries': 5,
    'retry_delay': 1500,
    'rssi_threshold': -85,
    'auto_reconnect': True,
    'gc_interval': 8,
    'memory_threshold': 40000,
    'watchdog_timeout': 30000,
    'operation_cooldown': 200
}