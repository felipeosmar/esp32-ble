# boot.py - Configuração de inicialização ESP32 BLE ADC Server
"""
Arquivo executado a cada boot do ESP32
Configurações otimizadas para aplicação BLE ADC
"""

# Desabilitar debug para economia de memória
import esp
esp.osdebug(0)

# Garbage collection inicial
import gc
gc.collect()

# Configurações de sistema
import machine
import time

print("=== ESP32 BLE ADC Server Boot ===")
print(f"Frequência CPU: {machine.freq()}Hz")
print(f"Memória livre: {gc.mem_free()} bytes")

# Configurar frequência para balance entre performance/energia
# 240MHz para máxima performance, 80MHz para economia
try:
    machine.freq(160000000)  # 160MHz - balance otimizado
    print(f"CPU ajustada para: {machine.freq()}Hz")
except:
    print("Mantendo frequência padrão do CPU")

# Desabilitar Wi-Fi para economizar energia (BLE apenas)
import network
try:
    wlan = network.WLAN(network.STA_IF)
    if wlan.active():
        wlan.active(False)
        print("Wi-Fi desabilitado (modo BLE only)")
except:
    pass

# Configuração de energia otimizada
try:
    # Desabilitar PowerSave do Wi-Fi (já desabilitado)
    pass
except:
    pass

print("Boot concluído - Sistema pronto!")
print("-" * 40)
