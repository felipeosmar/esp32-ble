"""
Programa BLE otimizado para ESP32 com MicroPython v1.25.0
- Gestão eficiente de memória RAM/Flash
- Máquina de estados robusta com timeouts
- Reconexão automática inteligente
- Processamento inline de dispositivos (sem cache)
- Operação contínua sem vazamentos
"""

import bluetooth
import struct
import time
import gc
import machine
from micropython import const

# Constantes de eventos BLE
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)

# UUIDs específicos                   
SENSOR_SERVICE_UUID = bluetooth.UUID("6E400000-B5A3-F393-E0A9-E50E24DCCA9E")
ANALOG_VALUE_CHAR_UUID = bluetooth.UUID("6E400000-B5A3-F393-E0A9-E50E24DCCA9E")
_CCCD_UUID = bluetooth.UUID(0x2902)
_NOTIFY_ENABLE = const(1)

# Estados da máquina - otimizado para ESP32
STATE_IDLE = const(0)
STATE_SCANNING = const(1)
STATE_CONNECTING = const(2)
STATE_CONNECTED = const(3)
STATE_DISCOVERING = const(4)
STATE_READY = const(5)
STATE_ERROR = const(6)
STATE_RECONNECTING = const(7)

class BLESensorClient:
    def __init__(self, target_mac=None, device_name=None, config=None):
        self.target_mac = target_mac
        self.device_name = device_name
        
        # Configuração otimizada para ESP32 - valores testados
        self.config = config or {
            'scan_duration': 25000,        # 25s - equilibrio entre descoberta e bateria
            'connection_timeout': 8000,     # 8s timeout conexão
            'discovery_timeout': 6000,      # 6s timeout descoberta
            'read_timeout': 4000,          # 4s timeout leitura
            'max_retries': 5,              # Mais tentativas
            'retry_delay': 1500,           # 1.5s entre tentativas
            'rssi_threshold': -85,         # RSSI mínimo
            'auto_reconnect': True,        # Reconexão automática
            'gc_interval': 8,              # Coleta lixo a cada 8 ops
            'memory_threshold': 40000,     # 40KB mínimo livre
            'watchdog_timeout': 30000,     # 30s watchdog
            'operation_cooldown': 200      # 200ms entre operações críticas
        }
        
        # Estados e controle
        self.state = STATE_IDLE
        self.previous_state = STATE_IDLE
        self.state_timestamp = 0
        
        # BLE handles
        self.ble = None
        self.conn_handle = None
        
        # Descoberta de serviços
        self.service_handles = None
        self.char_handle = None
        self.cccd_handle = None
        
        # APENAS dispositivo alvo (sem cache)
        self.target_device = None
        self.target_found = False
        
        # Controle de operações e recursos
        self.operation_count = 0
        self.last_operation_time = 0
        self.retry_count = 0
        self.error_count = 0
        self.last_gc_time = 0
        
        # Flags de estado
        self.service_discovered = False
        self.char_discovered = False
        self.notifications_enabled = False
        
        # Estatísticas para monitoramento
        self.stats = {
            'connections': 0,
            'disconnections': 0,
            'notifications': 0,
            'reads': 0,
            'errors': 0,
            'gc_collections': 0,
            'min_memory': 999999,
            'devices_analyzed': 0
        }
        
    def init_ble(self):
        """Inicialização BLE otimizada com verificação de recursos"""
        try:
            # Coleta preventiva e verificação de memória
            gc.collect()
            free_mem = gc.mem_free()
            print(f"Memória livre: {free_mem} bytes")
            
            if free_mem < self.config['memory_threshold']:
                print(f"ERRO: Memória insuficiente ({free_mem} < {self.config['memory_threshold']})")
                return False
            
            # Inicialização BLE
            self.ble = bluetooth.BLE()
            self.ble.active(True)
            self.ble.irq(self.ble_irq)
            
            self._change_state(STATE_IDLE)
            self.stats['min_memory'] = free_mem
            
            print(f"BLE inicializado - RAM disponível: {gc.mem_free()} bytes")
            return True
            
        except Exception as e:
            print(f"Erro init BLE: {e}")
            self._change_state(STATE_ERROR)
            return False
    
    def _change_state(self, new_state):
        """Mudança de estado com timestamp e validação"""
        if new_state != self.state:
            self.previous_state = self.state
            self.state = new_state
            self.state_timestamp = time.ticks_ms()
            
            states = ["IDLE", "SCANNING", "CONNECTING", "CONNECTED", 
                     "DISCOVERING", "READY", "ERROR", "RECONNECTING"]
            print(f"Estado: {states[self.state]}")
    
    def _check_timeout(self, timeout_ms):
        """Verifica timeout do estado atual"""
        return time.ticks_diff(time.ticks_ms(), self.state_timestamp) > timeout_ms
    
    def _manage_memory(self, force=False):
        """Gestão inteligente de memória - crítico para ESP32"""
        current_time = time.ticks_ms()
        
        # Coleta periódica ou forçada
        if (force or 
            self.operation_count % self.config['gc_interval'] == 0 or
            time.ticks_diff(current_time, self.last_gc_time) > 10000):
            
            gc.collect()
            free_mem = gc.mem_free()
            self.stats['gc_collections'] += 1
            self.last_gc_time = current_time
            
            # Atualiza estatística de memória mínima
            if free_mem < self.stats['min_memory']:
                self.stats['min_memory'] = free_mem
            
            # Verifica se memória está criticamente baixa
            if free_mem < self.config['memory_threshold']:
                print(f"AVISO: Memória baixa {free_mem} bytes")
                self._emergency_cleanup()
            
            return free_mem
        return gc.mem_free()
    
    def _emergency_cleanup(self):
        """Limpeza de emergência para ESP32"""
        # Força coleta múltipla
        for _ in range(3):
            gc.collect()
            time.sleep_ms(10)
        
        print(f"Limpeza de emergência - Memória: {gc.mem_free()} bytes")
    
    def ble_irq(self, event, data):
        """Handler IRQ otimizado com controle de recursos"""
        try:
            self.operation_count += 1
            self.last_operation_time = time.ticks_ms()
            
            # Dispatch otimizado com dict
            handlers = {
                _IRQ_SCAN_RESULT: self._handle_scan_result,
                _IRQ_SCAN_DONE: self._handle_scan_done,
                _IRQ_PERIPHERAL_CONNECT: self._handle_connect,
                _IRQ_PERIPHERAL_DISCONNECT: self._handle_disconnect,
                _IRQ_GATTC_SERVICE_RESULT: self._handle_service_result,
                _IRQ_GATTC_SERVICE_DONE: self._handle_service_done,
                _IRQ_GATTC_CHARACTERISTIC_RESULT: self._handle_characteristic_result,
                _IRQ_GATTC_CHARACTERISTIC_DONE: self._handle_characteristic_done,
                _IRQ_GATTC_DESCRIPTOR_RESULT: self._handle_descriptor_result,
                _IRQ_GATTC_DESCRIPTOR_DONE: self._handle_descriptor_done,
                _IRQ_GATTC_READ_RESULT: self._handle_read_result,
                _IRQ_GATTC_READ_DONE: self._handle_read_done,
                _IRQ_GATTC_NOTIFY: self._handle_notify,
                _IRQ_GATTC_WRITE_DONE: self._handle_write_done,
            }
            
            handler = handlers.get(event)
            if handler:
                handler(data)
            
            # Gestão de memória periódica
            self._manage_memory()
            
        except Exception as e:
            print(f"Erro IRQ: {e}")
            self.stats['errors'] += 1
            self.error_count += 1
            
            # Reset em caso de muitos erros
            if self.error_count > 15:
                print("Muitos erros - reiniciando BLE...")
                self._handle_critical_error()
    
    def _handle_scan_result(self, data):
        """PROCESSAMENTO INLINE - análise imediata de cada dispositivo"""
        if self.state != STATE_SCANNING:
            return
            
        addr_type, addr, adv_type, rssi, adv_data = data
        self.stats['devices_analyzed'] += 1
        
        # Filtro RSSI primeiro (mais eficiente)
        if rssi < self.config['rssi_threshold']:
            return
        
        # Processa endereço inline
        addr_str = ':'.join(['%02x' % b for b in addr])
        
        # Extração inline de dados (sem armazenamento)
        device_name = self._extract_device_name(adv_data)
        service_uuids = self._extract_service_uuids(adv_data)
        
        # Log compacto de debug
        print(f"Analisando: {addr_str[:8]}... RSSI:{rssi}dBm Nome:'{device_name or 'N/A'}'")
        
        # ANÁLISE INLINE - verifica se é dispositivo alvo
        if self._is_target_device(addr_str, device_name, service_uuids):
            print(f"*** ALVO ENCONTRADO: {addr_str} ***")
            
            # Salva APENAS o dispositivo alvo
            self.target_device = {
                'addr_type': addr_type,
                'addr': bytes(addr),  # Mantém como bytes para BLE
                'rssi': rssi,
                'name': device_name,
                'addr_str': addr_str
            }
            self.target_found = True
            
            # PARA scan imediatamente e conecta
            print(">>> Parando scan e conectando...")
            self._stop_scan()
            self._start_connection()
    
    def _handle_scan_done(self, data):
        """Scan concluído - resultado otimizado"""
        if self.target_found:
            # Dispositivo alvo já foi encontrado durante o scan
            print("Dispositivo alvo detectado durante scan")
        else:
            # Nenhum dispositivo alvo encontrado
            print(f"Dispositivo alvo não encontrado (analisados: {self.stats['devices_analyzed']})")
            self._change_state(STATE_IDLE)
    
    def _is_target_device(self, addr_str, device_name, service_uuids):
        """Identificação otimizada de dispositivo alvo - INLINE"""
        # 1. MAC específico (prioridade máxima)
        if self.target_mac and addr_str.lower() == self.target_mac.lower():
            return True
        
        # 2. Nome do dispositivo
        if (self.device_name and device_name and 
            self.device_name.lower() in device_name.lower()):
            return True
        
        # 3. UUID do serviço
        if service_uuids and SENSOR_SERVICE_UUID in service_uuids:
            return True
        
        return False
    
    def _stop_scan(self):
        """Para scan de forma segura"""
        try:
            self.ble.gap_scan(None)
            self._change_state(STATE_IDLE)
        except Exception as e:
            print(f"Erro parar scan: {e}")
    
    def _start_connection(self):
        """Inicia conexão com timeout e retry"""
        if not self.target_device:
            return False
        
        try:
            self._change_state(STATE_CONNECTING)
            self.retry_count = 0
            
            addr_type = self.target_device['addr_type']
            addr = self.target_device['addr']
            
            print(f"Conectando a {self.target_device['addr_str']}...")
            self.ble.gap_connect(addr_type, addr)
            return True
            
        except Exception as e:
            print(f"Erro conexão: {e}")
            self._change_state(STATE_ERROR)
            return False
    
    def _handle_connect(self, data):
        """Conexão estabelecida com descoberta automática"""
        conn_handle, addr_type, addr = data
        self.conn_handle = conn_handle
        self._change_state(STATE_CONNECTED)
        self.stats['connections'] += 1
        self.retry_count = 0  # Reset retry counter
        
        addr_str = ':'.join(['%02x' % b for b in addr])
        print(f"Conectado: {addr_str}")
        
        # Inicia descoberta imediatamente
        self._change_state(STATE_DISCOVERING)
        print("Descobrindo serviços...")
        
        try:
            self.ble.gattc_discover_services(self.conn_handle, SENSOR_SERVICE_UUID)
        except Exception as e:
            print(f"Erro descoberta: {e}")
            self._change_state(STATE_ERROR)
    
    def _handle_disconnect(self, data):
        """Desconexão com reconexão automática inteligente"""
        conn_handle, addr_type, addr = data
        self.conn_handle = None
        self._change_state(STATE_IDLE)
        self.stats['disconnections'] += 1
        
        # Reset de handles e flags
        self.service_handles = None
        self.char_handle = None
        self.cccd_handle = None
        self.service_discovered = False
        self.char_discovered = False
        self.notifications_enabled = False
        
        addr_str = ':'.join(['%02x' % b for b in addr])
        print(f"Desconectado: {addr_str}")
        
        # Reconexão automática se habilitada
        if (self.config['auto_reconnect'] and 
            self.retry_count < self.config['max_retries'] and
            self.target_device):
            
            self.retry_count += 1
            print(f"Reconexão {self.retry_count}/{self.config['max_retries']}")
            
            self._change_state(STATE_RECONNECTING)
            
            # Delay antes de tentar reconectar
            time.sleep_ms(self.config['retry_delay'])
            self._start_connection()
    
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
                self._change_state(STATE_ERROR)
        else:
            print("Serviço não encontrado!")
            self._change_state(STATE_ERROR)
    
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
                # Mesmo sem descritores, pode funcionar
                self._change_state(STATE_READY)
                print("Cliente pronto (sem notificações)")
        else:
            print("Característica não encontrada!")
            self._change_state(STATE_ERROR)
    
    def _handle_descriptor_result(self, data):
        """Resultado descoberta de descritores"""
        conn_handle, dsc_handle, uuid = data
        
        if bluetooth.UUID(uuid) == _CCCD_UUID:
            self.cccd_handle = dsc_handle
            print(f"CCCD: handle {dsc_handle}")
            
            try:
                # Habilita notificações
                self.ble.gattc_write(
                    conn_handle, dsc_handle, 
                    struct.pack('<h', _NOTIFY_ENABLE), 1
                )
                self.notifications_enabled = True
                self._change_state(STATE_READY)
                print("Cliente pronto com notificações")
            except Exception as e:
                print(f"Erro habilitar notif: {e}")
                self._change_state(STATE_READY)  # Continua sem notificações
    
    def _handle_descriptor_done(self, data):
        """Descoberta de descritores concluída"""
        if not self.notifications_enabled:
            # Não encontrou CCCD, mas pode continuar
            self._change_state(STATE_READY)
            print("Cliente pronto (sem notificações)")
    
    def _handle_read_result(self, data):
        """Resultado de leitura otimizado"""
        conn_handle, value_handle, char_data = data
        
        if value_handle == self.char_handle:
            self.stats['reads'] += 1
            
            if len(char_data) >= 2:
                analog_value = struct.unpack('<H', char_data[:2])[0]
                print(f"Valor: {analog_value}")
            else:
                print(f"Dados: {bytes(char_data).hex()}")
    
    def _handle_read_done(self, data):
        """Leitura concluída"""
        conn_handle, value_handle, status = data
        if status != 0:
            print(f"Erro leitura: status {status}")
    
    def _handle_notify(self, data):
        """Notificação otimizada"""
        conn_handle, value_handle, notify_data = data
        
        if value_handle == self.char_handle:
            self.stats['notifications'] += 1
            
            try:
                if len(notify_data) >= 2:
                    analog_value = struct.unpack('<H', notify_data[:2])[0]
                    print(f"Notif: {analog_value}")
                else:
                    print(f"Notif: {bytes(notify_data).hex()}")
            except Exception as e:
                print(f"Erro processar notif: {e}")
    
    def _handle_write_done(self, data):
        """Confirmação de escrita"""
        conn_handle, value_handle, status = data
        if status == 0:
            print("Escrita OK")
        else:
            print(f"Erro escrita: {status}")
    
    def _handle_critical_error(self):
        """Tratamento de erros críticos - reset do BLE"""
        print("ERRO CRÍTICO - Resetando BLE...")
        try:
            if self.ble:
                self.ble.active(False)
                time.sleep_ms(1000)
                self.ble.active(True)
                self.ble.irq(self.ble_irq)
            
            self._change_state(STATE_IDLE)
            self.error_count = 0
            self._manage_memory(force=True)
            
        except Exception as e:
            print(f"Erro no reset: {e}")
            # Último recurso
            print("Reiniciando ESP32...")
            time.sleep(2)
            machine.reset()
    
    def _extract_device_name(self, adv_data):
        """Extração otimizada de nome do dispositivo"""
        try:
            i = 0
            adv_len = len(adv_data)
            
            while i < adv_len - 1:
                length = adv_data[i]
                if length == 0 or i + length >= adv_len:
                    break
                
                data_type = adv_data[i + 1]
                
                # Nome completo (0x09) ou abreviado (0x08)
                if data_type in [0x08, 0x09]:
                    try:
                        name_data = adv_data[i + 2:i + 1 + length]
                        return name_data.decode('utf-8')
                    except:
                        pass
                
                i += 1 + length
        except:
            pass
        return None
    
    def _extract_service_uuids(self, adv_data):
        """Extração otimizada de UUIDs de serviços"""
        service_uuids = []
        try:
            i = 0
            adv_len = len(adv_data)
            
            while i < adv_len - 1:
                length = adv_data[i]
                if length == 0 or i + length >= adv_len:
                    break
                
                data_type = adv_data[i + 1]
                
                # UUIDs 16-bit (0x02, 0x03) ou 128-bit (0x06, 0x07)
                if data_type in [0x02, 0x03, 0x06, 0x07]:
                    try:
                        uuid_data = adv_data[i + 2:i + 1 + length]
                        
                        if data_type in [0x02, 0x03]:  # 16-bit
                            for j in range(0, len(uuid_data), 2):
                                if j + 1 < len(uuid_data):
                                    uuid_val = uuid_data[j] | (uuid_data[j+1] << 8)
                                    service_uuids.append(bluetooth.UUID(uuid_val))
                        
                        elif data_type in [0x06, 0x07]:  # 128-bit
                            for j in range(0, len(uuid_data), 16):
                                if j + 15 < len(uuid_data):
                                    uuid_bytes = uuid_data[j:j+16]
                                    service_uuids.append(bluetooth.UUID(uuid_bytes))
                    except:
                        pass
                
                i += 1 + length
        except:
            pass
        return service_uuids
    
    def scan_devices(self, duration_ms=None):
        """Scan otimizado com timeout e limpeza"""
        if self.state not in [STATE_IDLE, STATE_ERROR]:
            print(f"Estado inválido para scan: {self.state}")
            return False
        
        duration_ms = duration_ms or self.config['scan_duration']
        
        try:
            # Reset de contadores
            self.target_found = False
            self.target_device = None
            self.stats['devices_analyzed'] = 0
            self._manage_memory(force=True)
            
            print(f"Scan {duration_ms}ms (RAM: {gc.mem_free()}b)")
            print(f"Procurando: MAC='{self.target_mac or 'N/A'}' Nome='{self.device_name or 'N/A'}'")
            self._change_state(STATE_SCANNING)
            
            self.ble.gap_scan(duration_ms)
            return True
            
        except Exception as e:
            print(f"Erro scan: {e}")
            self._change_state(STATE_ERROR)
            return False
    
    def read_characteristic(self):
        """Leitura com verificação de estado"""
        if self.state != STATE_READY or not self.char_handle:
            print(f"Não pronto (estado: {self.state})")
            return False
        
        try:
            print("Lendo...")
            self.ble.gattc_read(self.conn_handle, self.char_handle)
            return True
        except Exception as e:
            print(f"Erro leitura: {e}")
            return False
    
    def write_characteristic(self, data):
        """Escrita com verificação de estado"""
        if self.state != STATE_READY or not self.char_handle:
            print("Não pronto para escrita")
            return False
        
        try:
            print(f"Escrevendo: {data}")
            self.ble.gattc_write(self.conn_handle, self.char_handle, data, 1)
            return True
        except Exception as e:
            print(f"Erro escrita: {e}")
            return False
    
    def is_ready(self):
        """Verifica se está pronto para operações"""
        return (self.state == STATE_READY and 
                self.char_handle is not None and
                self.conn_handle is not None)
    
    def get_status(self):
        """Status detalhado para debug"""
        states = ["IDLE", "SCANNING", "CONNECTING", "CONNECTED", 
                 "DISCOVERING", "READY", "ERROR", "RECONNECTING"]
        
        return {
            'state': states[self.state],
            'connected': self.conn_handle is not None,
            'ready': self.is_ready(),
            'target_found': self.target_found,
            'target_device': self.target_device['addr_str'] if self.target_device else None,
            'memory_free': gc.mem_free(),
            'min_memory': self.stats['min_memory'],
            'retry_count': self.retry_count,
            'stats': self.stats.copy()
        }
    
    def disconnect(self):
        """Desconexão limpa"""
        if self.conn_handle:
            try:
                self.config['auto_reconnect'] = False  # Evita reconexão
                self.ble.gap_disconnect(self.conn_handle)
                return True
            except Exception as e:
                print(f"Erro desconexão: {e}")
                return False
        return False

# Função principal otimizada
def main():
    print("=== Cliente BLE ESP32 Ultra-Otimizado ===")
    print(f"RAM inicial: {gc.mem_free()} bytes")
    
    # Configuração para operação contínua
    config = {
        'scan_duration': 60000,      # 60s scan
        'connection_timeout': 6000,   # 6s timeout
        'rssi_threshold': -100,       # RSSI mínimo
        'auto_reconnect': True,      # Reconexão automática  
        'max_retries': 8,            # Mais tentativas
        'gc_interval': 6,            # GC mais frequente
        'memory_threshold': 35000    # 35KB mínimo
    }
    
    # CONFIGURAÇÃO DO DISPOSITIVO ALVO
    TARGET_MAC = "c0:5d:89:b1:1e:aa"  # Ex: "84:ac:60:73:ef:dd"
    TARGET_NAME = "ADC-Server"  # Nome do dispositivo
    
    client = BLESensorClient(
        target_mac=TARGET_MAC,
        device_name=TARGET_NAME,
        config=config
    )
    
    if not client.init_ble():
        print("Falha na inicialização")
        return
    
    try:
        # Scan inicial
        print("\n>>> Iniciando scan otimizado...")
        if client.scan_devices():
            
            # Aguarda scan com timeout inteligente
            scan_timeout = time.ticks_ms() + config['scan_duration'] + 8000
            
            while time.ticks_diff(scan_timeout, time.ticks_ms()) > 0:
                if client.is_ready():
                    break
                
                # Mostra progresso
                if client.state == STATE_SCANNING:
                    print(".", end="")
                
                time.sleep_ms(500)
            
            print()  # Nova linha
            
            # Verifica resultado
            if client.is_ready():
                print("\n" + "="*40)
                print("CLIENTE PRONTO!")
                print("="*40)
                
                status = client.get_status()
                print(f"Estado: {status['state']}")
                print(f"Conectado a: {status['target_device']}")
                print(f"Memória: {status['memory_free']} bytes")
                print(f"Dispositivos analisados: {status['stats']['devices_analyzed']}")
                
                # Loop operacional otimizado
                print("\n>>> Iniciando operação contínua...")
                contador = 0
                
                while client.is_ready() and contador < 20:  # Demo com 20 leituras
                    contador += 1
                    print(f"\n--- Operação {contador} ---")
                    
                    # Status a cada 5 operações
                    if contador % 5 == 0:
                        status = client.get_status()
                        print(f"RAM: {status['memory_free']}b | "
                              f"Notif: {status['stats']['notifications']} | "
                              f"Erros: {status['stats']['errors']}")
                    
                    client.read_characteristic()
                    time.sleep(2)  # Intervalo entre leituras
                
                print("\nDemo concluída")
                
            else:
                print("\n" + "="*40)
                print("DISPOSITIVO ALVO NÃO ENCONTRADO")
                print("="*40)
                
                status = client.get_status()
                print(f"Dispositivos analisados: {status['stats']['devices_analyzed']}")
                print(f"Alvo procurado: MAC='{TARGET_MAC or 'N/A'}' Nome='{TARGET_NAME or 'N/A'}'")
                print(f"Status: {status}")
        
    except KeyboardInterrupt:
        print("\nInterrompido")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        print(f"Finalizando... RAM: {gc.mem_free()} bytes")
        client.disconnect()
        
        # Estatísticas finais
        stats = client.get_status()['stats']
        print(f"Estatísticas: Conexões: {stats['connections']}, "
              f"Dispositivos: {stats['devices_analyzed']}, "
              f"Notificações: {stats['notifications']}, "
              f"GC: {stats['gc_collections']}")

# Função auxiliar para conexão rápida
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

if __name__ == "__main__":
    main()