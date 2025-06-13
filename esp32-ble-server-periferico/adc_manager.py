# adc_manager.py - Gerenciamento dos canais ADC
"""
Módulo responsável pela leitura e processamento dos canais ADC
Implementa média móvel e conversão de valores
"""

from machine import Pin, ADC
import config

class ADCManager:
    """Gerenciador dos canais ADC com média móvel"""
    
    def __init__(self):
        """Inicializa os canais ADC e buffers"""
        self.adcs = []
        self.samples_buffer = []
        self.buffer_index = 0
        
        # Inicializar ADCs
        for pin in config.ADC_PINS:
            adc = ADC(Pin(pin))
            adc.atten(ADC.ATTN_11DB)  # Range 0-3.3V  
            adc.width(ADC.WIDTH_12BIT)  # Resolução 12 bits
            self.adcs.append(adc)
            
            # Inicializar buffer para este canal
            self.samples_buffer.append([0] * config.ADC_SAMPLES)
        
        print(f"ADC Manager inicializado - Canais: GPIO{config.ADC_PINS}")
    
    def read_channels(self):
        """
        Lê todos os canais ADC com média móvel
        
        Returns:
            list: Lista com dados de cada canal
        """
        values = []
        
        for i, adc in enumerate(self.adcs):
            # Leitura raw do ADC
            raw_value = adc.read()
            
            # Atualizar buffer circular
            self.samples_buffer[i][self.buffer_index] = raw_value
            
            # Calcular média móvel (otimizado para inteiros)
            avg_value = sum(self.samples_buffer[i]) // config.ADC_SAMPLES
            
            # Converter para voltagem
            voltage = avg_value * config.VOLTAGE_CONVERSION_FACTOR
            
            # Preparar dados do canal
            channel_data = {
                'channel': i + 1,
                'pin': config.ADC_PINS[i],
                'raw': avg_value,
                'voltage': round(voltage, 2)
            }
            
            values.append(channel_data)
        
        # Atualizar índice do buffer circular
        self.buffer_index = (self.buffer_index + 1) % config.ADC_SAMPLES
        
        return values
    
    def get_channel_count(self):
        """Retorna número de canais configurados"""
        return len(self.adcs)
    
    def get_raw_reading(self, channel_index):
        """
        Leitura direta sem processamento
        
        Args:
            channel_index (int): Índice do canal (0-2)
            
        Returns:
            int: Valor raw do ADC
        """
        if 0 <= channel_index < len(self.adcs):
            return self.adcs[channel_index].read()
        return 0
