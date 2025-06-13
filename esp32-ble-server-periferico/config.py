# config.py - Configurações centralizadas do sistema
"""
Arquivo de configuração para ESP32 BLE ADC Server
Centraliza todos os parâmetros configuráveis
"""

# Configurações dos canais ADC
ADC_PINS = [32, 33, 34]  # Pinos GPIO para os 3 canais analógicos
ADC_SAMPLES = 5          # Número de amostras para média móvel
ADC_ATTENUATION = 3      # ADC.ATTN_11DB (0-3.3V range)
ADC_WIDTH = 3            # ADC.WIDTH_12BIT (0-4095 range)
ADC_VOLTAGE_REF = 3.3    # Tensão de referência

# Configurações de timing
READ_INTERVAL_MS = 100   # Intervalo entre leituras (ms)
GC_INTERVAL_MS = 5000    # Intervalo para garbage collection (ms)
MAIN_LOOP_DELAY_MS = 10  # Delay no loop principal (ms)

# Configurações BLE
BLE_MESSAGE_MAX_LENGTH = 100  # Tamanho máximo da mensagem BLE
BLE_DEVICE_NAME = "ADC-Server"

# Configurações de debug
DEBUG_ENABLED = True
DEBUG_SHOW_RAW_VALUES = True

# Constantes calculadas
ADC_MAX_VALUE = (2 ** (ADC_WIDTH + 9)) - 1  # 4095 para 12 bits
VOLTAGE_CONVERSION_FACTOR = ADC_VOLTAGE_REF / ADC_MAX_VALUE
