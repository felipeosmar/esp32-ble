"""
Gerenciador de memória otimizado para ESP32
Gestão crítica de RAM limitada
"""

import gc
import time
from micropython import const

class MemoryManager:
    def __init__(self, config):
        self.config = config
        self.operation_count = 0
        self.last_gc_time = 0
        self.min_memory = 999999
        self.gc_collections = 0
    
    def manage_memory(self, force=False):
        """Gestão inteligente de memória - crítico para ESP32"""
        current_time = time.ticks_ms()
        
        # Coleta periódica ou forçada
        if (force or 
            self.operation_count % self.config['gc_interval'] == 0 or
            time.ticks_diff(current_time, self.last_gc_time) > 10000):
            
            gc.collect()
            free_mem = gc.mem_free()
            self.gc_collections += 1
            self.last_gc_time = current_time
            
            # Atualiza estatística de memória mínima
            if free_mem < self.min_memory:
                self.min_memory = free_mem
            
            # Verifica se memória está criticamente baixa
            if free_mem < self.config['memory_threshold']:
                print(f"AVISO: Memória baixa {free_mem} bytes")
                self.emergency_cleanup()
            
            return free_mem
        return gc.mem_free()
    
    def emergency_cleanup(self):
        """Limpeza de emergência para ESP32"""
        for _ in range(3):
            gc.collect()
            time.sleep_ms(10)
        
        print(f"Limpeza de emergência - Memória: {gc.mem_free()} bytes")
    
    def check_memory_health(self):
        """Verifica saúde da memória"""
        free_mem = gc.mem_free()
        return {
            'free': free_mem,
            'min_recorded': self.min_memory,
            'gc_count': self.gc_collections,
            'health': 'OK' if free_mem > self.config['memory_threshold'] else 'LOW'
        }
    
    def increment_operation(self):
        """Incrementa contador de operações"""
        self.operation_count += 1