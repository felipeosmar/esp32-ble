"""
Handlers de eventos BLE
Processamento otimizado de IRQs
"""

import struct
import time
from ble_constants import *
from adv_parser import AdvertisementParser

class BLEEventHandlers:
    def __init__(self, client):
        self.client = client
    
    def handle_scan_result(self, data):
        """PROCESSAMENTO INLINE - análise imediata de cada dispositivo"""
        if self.client.state_machine.state != STATE_SCANNING:
            return
            
        addr_type, addr, adv_type, rssi, adv_data = data
        self.client.stats['devices_analyzed'] += 1
        
        # Filtro RSSI primeiro (mais eficiente)
        if rssi < self.client.config['rssi_threshold']:
            return
        
        # Processa endereço inline
        addr_str = ':'.join(['%02x' % b for b in addr])
        
        # Extração inline de dados (sem armazenamento)
        device_name = AdvertisementParser.extract_device_name(adv_data)
        service_uuids = AdvertisementParser.extract_service_uuids(adv_data)
        
        # Log compacto de debug
        print(f"Analisando: {addr_str[:8]}... RSSI:{rssi}dBm Nome:'{device_name or 'N/A'}'")
        
        # ANÁLISE INLINE - verifica se é dispositivo alvo
        if AdvertisementParser.is_target_device(
            addr_str, device_name, service_uuids, 
            self.client.target_mac, self.client.device_name, SENSOR_SERVICE_UUID):
            
            print(f"*** ALVO ENCONTRADO: {addr_str} ***")
            
            # Salva APENAS o dispositivo alvo
            self.client.target_device = {
                'addr_type': addr_type,
                'addr': bytes(addr),
                'rssi': rssi,
                'name': device_name,
                'addr_str': addr_str
            }
            self.client.target_found = True
            
            # PARA scan imediatamente e conecta
            print(">>> Parando scan e conectando...")
            self.client._stop_scan()
            self.client._start_connection()
    
    def handle_scan_done(self, data):
        """Scan concluído"""
        if self.client.target_found:
            print("Dispositivo alvo detectado durante scan")
        else:
            print(f"Dispositivo alvo não encontrado (analisados: {self.client.stats['devices_analyzed']})")
            self.client.state_machine.change_state(STATE_IDLE)
    
    def handle_connect(self, data):
        """Conexão estabelecida"""
        conn_handle, addr_type, addr = data
        self.client.conn_handle = conn_handle
        self.client.state_machine.change_state(STATE_CONNECTED)
        self.client.stats['connections'] += 1
        self.client.retry_count = 0
        
        addr_str = ':'.join(['%02x' % b for b in addr])
        print(f"Conectado: {addr_str}")
        
        # Inicia descoberta imediatamente
        self.client.state_machine.change_state(STATE_DISCOVERING)
        print("Descobrindo serviços...")
        
        try:
            self.client.ble.gattc_discover_services(self.client.conn_handle, SENSOR_SERVICE_UUID)
        except Exception as e:
            print(f"Erro descoberta: {e}")
            self.client.state_machine.change_state(STATE_ERROR)
    
    def handle_disconnect(self, data):
        """Desconexão com reconexão automática"""
        conn_handle, addr_type, addr = data
        self.client.conn_handle = None
        self.client.state_machine.change_state(STATE_IDLE)
        self.client.stats['disconnections'] += 1
        
        # Reset de handles e flags
        self.client._reset_connection_state()
        
        addr_str = ':'.join(['%02x' % b for b in addr])
        print(f"Desconectado: {addr_str}")
        
        # Reconexão automática se habilitada
        if (self.client.config['auto_reconnect'] and 
            self.client.retry_count < self.client.config['max_retries'] and
            self.client.target_device):
            
            self.client.retry_count += 1
            print(f"Reconexão {self.client.retry_count}/{self.client.config['max_retries']}")
            
            self.client.state_machine.change_state(STATE_RECONNECTING)
            time.sleep_ms(self.client.config['retry_delay'])
            self.client._start_connection()
    
    def handle_notify(self, data):
        """Notificação otimizada"""
        conn_handle, value_handle, notify_data = data
        
        if value_handle == self.client.char_handle:
            self.client.stats['notifications'] += 1
            
            try:
                if len(notify_data) >= 2:
                    analog_value = struct.unpack('<H', notify_data[:2])[0]
                    print(f"Notif: {analog_value}")
                else:
                    print(f"Notif: {bytes(notify_data).hex()}")
            except Exception as e:
                print(f"Erro processar notif: {e}")
    
    def handle_read_result(self, data):
        """Resultado de leitura otimizado"""
        conn_handle, value_handle, char_data = data
        
        if value_handle == self.client.char_handle:
            self.client.stats['reads'] += 1
            
            if len(char_data) >= 2:
                analog_value = struct.unpack('<H', char_data[:2])[0]
                print(f"Valor: {analog_value}")
            else:
                print(f"Dados: {bytes(char_data).hex()}")