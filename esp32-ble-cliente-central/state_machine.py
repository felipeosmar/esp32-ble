"""
Máquina de estados BLE otimizada
Controle de fluxo e timeouts
"""

import time
from ble_constants import STATE_NAMES

class StateMachine:
    def __init__(self):
        self.state = 0  # STATE_IDLE
        self.previous_state = 0
        self.state_timestamp = 0
    
    def change_state(self, new_state):
        """Mudança de estado com timestamp e validação"""
        if new_state != self.state:
            self.previous_state = self.state
            self.state = new_state
            self.state_timestamp = time.ticks_ms()
            print(f"Estado: {STATE_NAMES[self.state]}")
    
    def check_timeout(self, timeout_ms):
        """Verifica timeout do estado atual"""
        return time.ticks_diff(time.ticks_ms(), self.state_timestamp) > timeout_ms
    
    def get_state_name(self):
        """Retorna nome do estado atual"""
        return STATE_NAMES[self.state]
    
    def get_state_duration(self):
        """Retorna duração do estado atual em ms"""
        return time.ticks_diff(time.ticks_ms(), self.state_timestamp)