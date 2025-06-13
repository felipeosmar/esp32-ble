"""
Utilitários auxiliares
Funções de conveniência e helpers
"""

import time
from ble_client import BLESensorClient

def conectar_dispositivo(mac_address=None, device_name=None, timeout_s=30):
    """Conecta rapidamente a um dispositivo específico"""
    config = {'scan_duration': min(timeout_s * 1000, 25000)}
    client = BLESensorClient(target_mac=mac_address, device_name=device_name, config=config)
    
    if not client.init_ble():
        return None
    
    if client.scan_devices():
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_s * 1000:
            if client.is_ready():
                return client
            time.sleep_ms(100)
    
    return None

def scan_nearby_devices(duration_s=10, rssi_min=-90):
    """Escaneia dispositivos próximos (modo descoberta)"""
    config = {
        'scan_duration': duration_s * 1000,
        'rssi_threshold': rssi_min
    }
    
    client = BLESensorClient(config=config)
    if client.init_ble():
        print(f"Escaneando por {duration_s}s...")
        client.scan_devices()
        return client
    return None

def get_memory_info():
    """Informações detalhadas de memória"""
    import gc
    gc.collect()
    return {
        'free': gc.mem_free(),
        'allocated': gc.mem_alloc(),
        'total': gc.mem_free() + gc.mem_alloc()
    }