# utils.py - Utilitários e funções auxiliares
"""
Funções utilitárias para debug, formatação e operações auxiliares
"""

import time
import gc
import config

class SystemUtils:
    """Utilitários do sistema"""
    
    @staticmethod
    def print_debug(message, show_timestamp=True):
        """
        Print com controle de debug
        
        Args:
            message (str): Mensagem para debug
            show_timestamp (bool): Mostrar timestamp
        """
        if config.DEBUG_ENABLED:
            if show_timestamp:
                timestamp = time.ticks_ms()
                print(f"[{timestamp}] {message}")
            else:
                print(message)
    
    @staticmethod
    def print_channel_data(analog_data):
        """
        Exibe dados dos canais formatados
        
        Args:
            analog_data (list): Dados dos canais ADC
        """
        if not config.DEBUG_ENABLED:
            return
            
        for data in analog_data:
            if config.DEBUG_SHOW_RAW_VALUES:
                print(f"  Canal {data['channel']} (GPIO{data['pin']}): "
                      f"{data['voltage']}V (raw: {data['raw']})")
            else:
                print(f"  Canal {data['channel']}: {data['voltage']}V")
    
    @staticmethod
    def memory_info():
        """
        Retorna informações de memória
        
        Returns:
            dict: Informações de memória
        """
        try:
            import micropython
            return {
                'free_memory': gc.mem_free(),
                'allocated_memory': gc.mem_alloc()
            }
        except ImportError:
            return {'error': 'micropython module not available'}
    
    @staticmethod
    def perform_gc():
        """Executa garbage collection e retorna memória liberada"""
        mem_before = gc.mem_free()
        gc.collect()
        mem_after = gc.mem_free()
        freed = mem_after - mem_before
        
        if config.DEBUG_ENABLED and freed > 0:
            print(f"GC: {freed} bytes liberados")
        
        return freed
    
    @staticmethod
    def uptime_seconds():
        """
        Retorna tempo de execução em segundos
        
        Returns:
            float: Tempo em segundos
        """
        return time.ticks_ms() / 1000
    
    @staticmethod
    def format_uptime():
        """
        Formata tempo de execução
        
        Returns:
            str: Tempo formatado (ex: "1h 23m 45s")
        """
        seconds = int(SystemUtils.uptime_seconds())
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

class DataValidator:
    """Validador de dados"""
    
    @staticmethod
    def validate_adc_data(analog_data):
        """
        Valida dados do ADC
        
        Args:
            analog_data (list): Dados para validar
            
        Returns:
            bool: True se dados válidos
        """
        if not isinstance(analog_data, list):
            return False
        
        for data in analog_data:
            if not isinstance(data, dict):
                return False
            
            required_keys = ['channel', 'raw', 'voltage']
            if not all(key in data for key in required_keys):
                return False
            
            # Validar ranges
            if not (0 <= data['raw'] <= config.ADC_MAX_VALUE):
                return False
            
            if not (0 <= data['voltage'] <= config.ADC_VOLTAGE_REF):
                return False
        
        return True
    
    @staticmethod
    def sanitize_voltage(voltage):
        """
        Sanitiza valor de voltagem
        
        Args:
            voltage (float): Valor para sanitizar
            
        Returns:
            float: Valor sanitizado
        """
        if voltage < 0:
            return 0.0
        elif voltage > config.ADC_VOLTAGE_REF:
            return config.ADC_VOLTAGE_REF
        else:
            return round(voltage, 2)
