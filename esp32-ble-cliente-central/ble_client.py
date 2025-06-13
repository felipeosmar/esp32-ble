"""
Cliente BLE principal otimizado para ESP32
Classe principal com integração de todos os módulos
"""

import bluetooth
import struct
import time
import gc
import machine

from ble_constants import *
from memory_manager import MemoryManager
from state_machine import StateMachine
from ble_handlers import BLEEventHandlers

class BLESensorClient:
    def __init__(self, target_mac=None, device_name=None, config=None):
        self.target_mac = target_mac
        self.device_name = device_name
        
        # Correção: Sintaxe compatível com MicroPython v1.25.0
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # Componentes modulares
        self.memory_manager = MemoryManager(self.config)
        self.state_machine = StateMachine()
        self.handlers = BLEEventHandlers(self)
        
        # BLE handles
        self.ble = None
        self.conn_handle = None
        
        # Descoberta de serviços
        self.service_handles = None
        self.char_handle = None
        self.cccd_handle = None
        
        # Dispositivo alvo (sem cache)
        self.target_device = None
        self.target_found = False
        
        # Controle de operações
        self.last_operation_time = 0
        self.retry_count = 0
        self.error_count = 0
        
        # Flags de estado
        self.service_discovered = False
        self.char_discovered = False
        self.notifications_enabled = False
        
        # Estatísticas
        self.stats = {
            'connections': 0,
            'disconnections': 0,
            'notifications': 0,
            'reads': 0,
            'errors': 0,
            'devices_analyzed': 0
        }
    
    def init_ble(self):
        """Inicialização BLE otimizada"""
        try:
            gc.collect()
            free_mem = gc.mem_free()
            print(f"Memória livre: {free_mem} bytes")
            
            if free_mem < self.config['memory_threshold']:
                print(f"ERRO: Memória insuficiente ({free_mem} < {self.config['memory_threshold']})")
                return False
            
            self.ble = bluetooth.BLE()
            self.ble.active(True)
            self.ble.irq(self.ble_irq)
            
            self.state_machine.change_state(STATE_IDLE)
            self.memory_manager.min_memory = free_mem
            
            print(f"BLE inicializado - RAM disponível: {gc.mem_free()} bytes")
            return True
            
        except Exception as e:
            print(f"Erro init BLE: {e}")
            self.state_machine.change_state(STATE_ERROR)
            return False
    
    def ble_irq(self, event, data):
        """Handler IRQ otimizado com dispatch"""
        try:
            self.memory_manager.increment_operation()
            self.last_operation_time = time.ticks_ms()
            
            # Dispatch otimizado
            handlers_map = {
                IRQ_SCAN_RESULT: self.handlers.handle_scan_result,
                IRQ_SCAN_DONE: self.handlers.handle_scan_done,
                IRQ_PERIPHERAL_CONNECT: self.handlers.handle_connect,
                IRQ_PERIPHERAL_DISCONNECT: self.handlers.handle_disconnect,
                IRQ_GATTC_SERVICE_RESULT: self._handle_service_result,
                IRQ_GATTC_SERVICE_DONE: self._handle_service_done,
                IRQ_GATTC_CHARACTERISTIC_RESULT: self._handle_characteristic_result,
                IRQ_GATTC_CHARACTERISTIC_DONE: self._handle_characteristic_done,
                IRQ_GATTC_DESCRIPTOR_RESULT: self._handle_descriptor_result,
                IRQ_GATTC_DESCRIPTOR_DONE: self._handle_descriptor_done,
                IRQ_GATTC_READ_RESULT: self.handlers.handle_read_result,
                IRQ_GATTC_READ_DONE: self._handle_read_done,
                IRQ_GATTC_NOTIFY: self.handlers.handle_notify,
                IRQ_GATTC_WRITE_DONE: self._handle_write_done,
            }
            
            handler = handlers_map.get(event)
            if handler:
                handler(data)
            
            # Gestão de memória periódica
            self.memory_manager.manage_memory()
            
        except Exception as e:
            print(f"Erro IRQ: {e}")
            self.stats['errors'] += 1
            self.error_count += 1
            
            if self.error_count > 15:
                self._handle_critical_error()
    
    def scan_devices(self, duration_ms=None):
        """Scan otimizado"""
        if self.state_machine.state not in [STATE_IDLE, STATE_ERROR]:
            print(f"Estado inválido para scan: {self.state_machine.get_state_name()}")
            return False
        
        duration_ms = duration_ms or self.config['scan_duration']
        
        try:
            # Reset de contadores
            self.target_found = False
            self.target_device = None
            self.stats['devices_analyzed'] = 0
            self.memory_manager.manage_memory(force=True)
            
            print(f"Scan {duration_ms}ms (RAM: {gc.mem_free()}b)")
            print(f"Procurando: MAC='{self.target_mac or 'N/A'}' Nome='{self.device_name or 'N/A'}'")
            self.state_machine.change_state(STATE_SCANNING)
            
            self.ble.gap_scan(duration_ms)
            return True
            
        except Exception as e:
            print(f"Erro scan: {e}")
            self.state_machine.change_state(STATE_ERROR)
            return False
    
    def read_characteristic(self):
        """Leitura com verificação de estado"""
        if self.state_machine.state != STATE_READY or not self.char_handle:
            print(f"Não pronto (estado: {self.state_machine.get_state_name()})")
            return False
        
        try:
            print("Lendo...")
            self.ble.gattc_read(self.conn_handle, self.char_handle)
            return True
        except Exception as e:
            print(f"Erro leitura: {e}")
            return False
    
    def is_ready(self):
        """Verifica se está pronto para operações"""
        return (self.state_machine.state == STATE_READY and 
                self.char_handle is not None and
                self.conn_handle is not None)
    
    def get_status(self):
        """Status detalhado"""
        memory_info = self.memory_manager.check_memory_health()
        
        # Correção: Evita unpacking de dict para compatibilidade
        stats_copy = self.stats.copy()
        stats_copy['gc_collections'] = memory_info['gc_count']
        
        return {
            'state': self.state_machine.get_state_name(),
            'connected': self.conn_handle is not None,
            'ready': self.is_ready(),
            'target_found': self.target_found,
            'target_device': self.target_device['addr_str'] if self.target_device else None,
            'memory_free': memory_info['free'],
            'min_memory': memory_info['min_recorded'],
            'retry_count': self.retry_count,
            'stats': stats_copy
        }
    
    def disconnect(self):
        """Desconexão limpa"""
        if self.conn_handle:
            try:
                self.config['auto_reconnect'] = False
                self.ble.gap_disconnect(self.conn_handle)
                return True
            except Exception as e:
                print(f"Erro desconexão: {e}")
                return False
        return False
    
    def _reset_connection_state(self):
        """Reset estado de conexão"""
        self.service_handles = None
        self.char_handle = None
        self.cccd_handle = None
        self.service_discovered = False
        self.char_discovered = False
        self.notifications_enabled = False
    
    def _stop_scan(self):
        """Para scan seguramente"""
        try:
            self.ble.gap_scan(None)
            self.state_machine.change_state(STATE_IDLE)
        except Exception as e:
            print(f"Erro parar scan: {e}")
    
    def _start_connection(self):
        """Inicia conexão"""
        if not self.target_device:
            return False
        
        try:
            self.state_machine.change_state(STATE_CONNECTING)
            self.retry_count = 0
            
            addr_type = self.target_device['addr_type']
            addr = self.target_device['addr']
            
            print(f"Conectando a {self.target_device['addr_str']}...")
            self.ble.gap_connect(addr_type, addr)
            return True
            
        except Exception as e:
            print(f"Erro conexão: {e}")
            self.state_machine.change_state(STATE_ERROR)
            return False
    
    def _handle_critical_error(self):
        """Tratamento de erros críticos"""
        print("ERRO CRÍTICO - Resetando BLE...")
        try:
            if self.ble:
                self.ble.active(False)
                time.sleep_ms(1000)
                self.ble.active(True)
                self.ble.irq(self.ble_irq)
            
            self.state_machine.change_state(STATE_IDLE)
            self.error_count = 0
            self.memory_manager.manage_memory(force=True)
            
        except Exception as e:
            print(f"Erro no reset: {e}")
            print("Reiniciando ESP32...")
            time.sleep(2)
            machine.reset()
    
    # Handlers de descoberta GATT (métodos restantes simplificados)
    def _handle_service_result(self, data):
        """Resultado descoberta de serviços"""
        conn_handle, start_handle, end_handle, uuid = data
        if bluetooth.UUID(uuid) == SENSOR_SERVICE_UUID:
            self.service_handles = (start_handle, end_handle)
            self.service_discovered = True
            print(f"Serviço encontrado: {start_handle}-{end_handle}")
    
    def _handle_service_done(self, data):
        """Descoberta de serviços concluída"""
        if self.service_discovered:
            print("Descobrindo características...")
            start_handle, end_handle = self.service_handles
            try:
                self.ble.gattc_discover_characteristics(
                    self.conn_handle, start_handle, end_handle, ANALOG_VALUE_CHAR_UUID
                )
            except Exception as e:
                print(f"Erro descoberta chars: {e}")
                self.state_machine.change_state(STATE_ERROR)
        else:
            print("Serviço não encontrado!")
            self.state_machine.change_state(STATE_ERROR)
    
    def _handle_characteristic_result(self, data):
        """Resultado descoberta de características"""
        conn_handle, end_handle, value_handle, properties, uuid = data
        if bluetooth.UUID(uuid) == ANALOG_VALUE_CHAR_UUID:
            self.char_handle = value_handle
            self.char_discovered = True
            print(f"Característica: handle {value_handle}")
    
    def _handle_characteristic_done(self, data):
        """Descoberta características concluída"""
        if self.char_discovered:
            print("Descobrindo descritores...")
            try:
                self.ble.gattc_discover_descriptors(
                    self.conn_handle, self.char_handle, self.char_handle + 2
                )
            except Exception as e:
                print(f"Erro descritores: {e}")
                self.state_machine.change_state(STATE_READY)
                print("Cliente pronto (sem notificações)")
        else:
            print("Característica não encontrada!")
            self.state_machine.change_state(STATE_ERROR)
    
    def _handle_descriptor_result(self, data):
        """Resultado descoberta de descritores"""
        conn_handle, dsc_handle, uuid = data
        if bluetooth.UUID(uuid) == CCCD_UUID:
            self.cccd_handle = dsc_handle
            print(f"CCCD: handle {dsc_handle}")
            
            try:
                self.ble.gattc_write(
                    conn_handle, dsc_handle, 
                    struct.pack('<h', NOTIFY_ENABLE), 1
                )
                self.notifications_enabled = True
                self.state_machine.change_state(STATE_READY)
                print("Cliente pronto com notificações")
            except Exception as e:
                print(f"Erro habilitar notif: {e}")
                self.state_machine.change_state(STATE_READY)
    
    def _handle_descriptor_done(self, data):
        """Descoberta de descritores concluída"""
        if not self.notifications_enabled:
            self.state_machine.change_state(STATE_READY)
            print("Cliente pronto (sem notificações)")
    
    def _handle_read_done(self, data):
        """Leitura concluída"""
        conn_handle, value_handle, status = data
        if status != 0:
            print(f"Erro leitura: status {status}")
    
    def _handle_write_done(self, data):
        """Confirmação de escrita"""
        conn_handle, value_handle, status = data
        if status == 0:
            print("Escrita OK")
        else:
            print(f"Erro escrita: {status}")