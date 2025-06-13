"""
Programa BLE para ESP32 com MicroPython v1.25.0
- Escaneia dispositivos BLE 
- Conecta a servidor BLE específico
- Acessa serviços e características por UUID personalizado
"""

import bluetooth
import struct
import time
import gc
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
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)

# UUIDs específicos fornecidos
SENSOR_SERVICE_UUID = bluetooth.UUID("c1a1b328-343c-4545-9aa4-a7453457d543")
ANALOG_VALUE_CHAR_UUID = bluetooth.UUID("c1a2b328-343c-4545-9aa4-a7453457d543")

# UUID do Client Characteristic Configuration Descriptor
_CCCD_UUID = bluetooth.UUID(0x2902)
_NOTIFY_ENABLE = const(1)

class BLESensorClient:
    def __init__(self, target_mac=None, device_name=None):
        self.target_mac = target_mac  # Endereço MAC específico
        self.device_name = device_name  # Nome do dispositivo (opcional)
        self.ble = None
        self.conn_handle = None
        self.connected = False
        self.scanning = False
        
        # Informações do serviço descoberto
        self.service_handles = None
        self.char_handle = None
        self.cccd_handle = None
        
        # Dispositivos encontrados durante scan
        self.found_devices = {}
        self.target_device = None
        
        # Estados de descoberta
        self.service_discovered = False
        self.char_discovered = False
        
        # Configurações
        self.max_retries = 3
        self.scan_duration = 60000  # 60 segundos
        
    def init_ble(self):
        """Inicializa BLE"""
        try:
            print("Inicializando BLE...")
            
            # Inicializa BLE
            self.ble = bluetooth.BLE()
            self.ble.active(True)
            self.ble.irq(self.ble_irq)
            
            print("BLE inicializado com sucesso")
            return True
            
        except Exception as e:
            print(f"Erro na inicialização BLE: {e}")
            return False
    
    def ble_irq(self, event, data):
        """Handler IRQ BLE"""
        try:
            if event == _IRQ_SCAN_RESULT:
                self._handle_scan_result(data)
            elif event == _IRQ_SCAN_DONE:
                self._handle_scan_done(data)
            elif event == _IRQ_PERIPHERAL_CONNECT:
                self._handle_connect(data)
            elif event == _IRQ_PERIPHERAL_DISCONNECT:
                self._handle_disconnect(data)
            elif event == _IRQ_GATTC_SERVICE_RESULT:
                self._handle_service_result(data)
            elif event == _IRQ_GATTC_SERVICE_DONE:
                self._handle_service_done(data)
            elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
                self._handle_characteristic_result(data)
            elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
                self._handle_characteristic_done(data)
            elif event == _IRQ_GATTC_DESCRIPTOR_RESULT:
                self._handle_descriptor_result(data)
            elif event == _IRQ_GATTC_READ_RESULT:
                self._handle_read_result(data)
            elif event == _IRQ_GATTC_NOTIFY:
                self._handle_notify(data)
            elif event == _IRQ_GATTC_WRITE_DONE:
                self._handle_write_done(data)
        except Exception as e:
            print(f"Erro no BLE IRQ: {e}")
    
    def _handle_scan_result(self, data):
        """Processa resultado do scan BLE"""
        addr_type, addr, adv_type, rssi, adv_data = data
        
        # Converte endereço para string
        addr_str = ':'.join(['%02x' % b for b in addr])
        
        # Filtra por força do sinal
        if rssi > -90:  # Aumentado o range para capturar mais dispositivos
            # Extrai nome do dispositivo
            device_name = self._extract_device_name(adv_data)
            
            # Extrai UUIDs de serviços se disponíveis
            service_uuids = self._extract_service_uuids(adv_data)
            
            # Mostra informações detalhadas
            name_info = f" - {device_name}" if device_name else ""
            service_info = f" - Serviços: {len(service_uuids)}" if service_uuids else ""
            print(f"Dispositivo: {addr_str}, RSSI: {rssi} dBm{name_info}{service_info}")
            
            # Armazena informações do dispositivo
            self.found_devices[addr_str] = {
                'addr_type': addr_type,
                'addr': bytes(addr),
                'rssi': rssi,
                'adv_data': bytes(adv_data),
                'name': device_name,
                'service_uuids': service_uuids
            }
            
            # Verifica se é o dispositivo alvo
            is_target = False
            
            # 1. Verifica por MAC address específico
            if self.target_mac and addr_str.lower() == self.target_mac.lower():
                print(f"*** DISPOSITIVO ALVO ENCONTRADO POR MAC: {addr_str} ***")
                is_target = True
            
            # 2. Verifica por nome do dispositivo
            elif self.device_name and device_name:
                if self.device_name.lower() in device_name.lower():
                    print(f"*** DISPOSITIVO ALVO ENCONTRADO POR NOME: {device_name} ***")
                    is_target = True
            
            # 3. Verifica por UUID do serviço nos dados de advertisement
            elif service_uuids and SENSOR_SERVICE_UUID in service_uuids:
                print(f"*** DISPOSITIVO ALVO ENCONTRADO POR UUID DE SERVIÇO ***")
                is_target = True
            
            if is_target:
                self.target_device = self.found_devices[addr_str]
                
                # INTERROMPE O SCAN IMEDIATAMENTE
                print(">>> INTERROMPENDO SCAN - DISPOSITIVO ALVO ENCONTRADO <<<")
                try:
                    self.ble.gap_scan(None)  # Para o scan
                    self.scanning = False
                except Exception as e:
                    print(f"Erro ao parar scan: {e}")
                
                # INICIA CONEXÃO IMEDIATAMENTE
                print(">>> INICIANDO CONEXÃO IMEDIATA <<<")
                self._connect_to_target()
    
    def _extract_device_name(self, adv_data):
        """Extrai nome do dispositivo dos dados de advertisement"""
        try:
            i = 0
            while i < len(adv_data):
                if i >= len(adv_data):
                    break
                    
                length = adv_data[i]
                if length == 0 or i + length >= len(adv_data):
                    break
                    
                data_type = adv_data[i + 1]
                
                # Tipo 0x08 = Shortened Local Name, 0x09 = Complete Local Name
                if data_type == 0x08 or data_type == 0x09:
                    try:
                        name_data = adv_data[i + 2:i + 1 + length]
                        return name_data.decode('utf-8')
                    except:
                        pass
                        
                i += 1 + length
        except Exception as e:
            pass
        return None
    
    def _extract_service_uuids(self, adv_data):
        """Extrai UUIDs de serviços dos dados de advertisement"""
        service_uuids = []
        try:
            i = 0
            while i < len(adv_data):
                if i >= len(adv_data):
                    break
                    
                length = adv_data[i]
                if length == 0 or i + length >= len(adv_data):
                    break
                    
                data_type = adv_data[i + 1]
                
                # Tipos de UUID de serviços:
                # 0x02 = 16-bit UUIDs incomplete
                # 0x03 = 16-bit UUIDs complete  
                # 0x06 = 128-bit UUIDs incomplete
                # 0x07 = 128-bit UUIDs complete
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
        except Exception as e:
            pass
        return service_uuids
    
    def _handle_scan_done(self, data):
        """Scan concluído"""
        self.scanning = False
        print(f"\n=== SCAN CONCLUÍDO ===")
        print(f"Total de dispositivos encontrados: {len(self.found_devices)}")
        
        # Se já tem dispositivo alvo (interrompeu o scan), não precisa fazer nada
        # A conexão já foi iniciada em _handle_scan_result
        if self.target_device:
            print(">>> Scan interrompido - conexão já iniciada <<<")
            return
        
        # Scan terminou sem encontrar dispositivo alvo
        if self.found_devices:
            print("\nDispositivos encontrados:")
            for i, (addr, info) in enumerate(self.found_devices.items(), 1):
                name = info.get('name', 'Nome desconhecido')
                rssi = info['rssi']
                services = len(info.get('service_uuids', []))
                print(f"{i:2d}. {addr} | RSSI: {rssi:3d} dBm | {name} | Serviços: {services}")
        
            print("\n>>> Dispositivo alvo não encontrado automaticamente.")
            print("Opções:")
            print("1. Especifique um MAC address específico")
            print("2. Modifique o nome do dispositivo procurado") 
            print("3. Use conectar_por_mac() para conectar manualmente")
            
            # Tenta conectar automaticamente ao dispositivo com melhor sinal
            melhor_dispositivo = max(self.found_devices.items(), 
                                   key=lambda x: x[1]['rssi'])
            melhor_mac = melhor_dispositivo[0]
            melhor_rssi = melhor_dispositivo[1]['rssi']
            
            print(f"\n>>> Tentando conectar ao dispositivo com melhor sinal:")
            print(f"    {melhor_mac} (RSSI: {melhor_rssi} dBm)")
            
            self.target_device = melhor_dispositivo[1]
            self._connect_to_target()
        else:
            print("Nenhum dispositivo encontrado!")
            
    def conectar_por_mac(self, mac_address):
        """Conecta diretamente a um dispositivo pelo MAC address"""
        mac_lower = mac_address.lower()
        
        if mac_lower in [addr.lower() for addr in self.found_devices.keys()]:
            # Encontra o dispositivo pelo MAC
            for addr, info in self.found_devices.items():
                if addr.lower() == mac_lower:
                    self.target_device = info
                    print(f"Selecionado dispositivo: {addr}")
                    return self._connect_to_target()
        else:
            print(f"Dispositivo {mac_address} não foi encontrado no scan")
            return False
    
    def listar_dispositivos(self):
        """Lista todos os dispositivos encontrados"""
        if not self.found_devices:
            print("Nenhum dispositivo encontrado. Execute scan primeiro.")
            return
            
        print("\nDispositivos disponíveis:")
        for i, (addr, info) in enumerate(self.found_devices.items(), 1):
            name = info.get('name', 'Nome desconhecido')
            rssi = info['rssi']
            services = len(info.get('service_uuids', []))
            print(f"{i:2d}. {addr} | RSSI: {rssi:3d} dBm | {name} | Serviços: {services}")
    
    def conectar_por_indice(self, indice):
        """Conecta ao dispositivo pelo índice da lista"""
        if not self.found_devices:
            print("Nenhum dispositivo encontrado")
            return False
            
        dispositivos_lista = list(self.found_devices.items())
        if 1 <= indice <= len(dispositivos_lista):
            addr, info = dispositivos_lista[indice - 1]
            self.target_device = info
            print(f"Selecionado dispositivo {indice}: {addr}")
            return self._connect_to_target()
        else:
            print(f"Índice inválido. Use valores entre 1 e {len(dispositivos_lista)}")
            return False
    
    def _connect_to_target(self):
        """Conecta ao dispositivo alvo"""
        if not self.target_device:
            print("Nenhum dispositivo alvo definido")
            return False
            
        try:
            addr_type = self.target_device['addr_type']
            addr = self.target_device['addr']
            
            print(f"Conectando...")
            # Sem argumentos nomeados na v1.25.0
            self.ble.gap_connect(addr_type, addr)
            return True
            
        except Exception as e:
            print(f"Erro na conexão: {e}")
            return False
    
    def _handle_connect(self, data):
        """Conexão estabelecida"""
        conn_handle, addr_type, addr = data
        self.conn_handle = conn_handle
        self.connected = True
        
        addr_str = ':'.join(['%02x' % b for b in addr])
        print(f"Conectado ao dispositivo {addr_str}")
        
        # Inicia descoberta de serviços
        print("Descobrindo serviços...")
        self.ble.gattc_discover_services(self.conn_handle, SENSOR_SERVICE_UUID)
    
    def _handle_disconnect(self, data):
        """Desconexão"""
        conn_handle, addr_type, addr = data
        self.conn_handle = None
        self.connected = False
        self.service_discovered = False
        self.char_discovered = False
        
        addr_str = ':'.join(['%02x' % b for b in addr])
        print(f"Desconectado do dispositivo {addr_str}")
    
    def _handle_service_result(self, data):
        """Resultado da descoberta de serviços"""
        conn_handle, start_handle, end_handle, uuid = data
        
        # Verifica se é o serviço alvo
        if bluetooth.UUID(uuid) == SENSOR_SERVICE_UUID:
            self.service_handles = (start_handle, end_handle)
            self.service_discovered = True
            print(f"Serviço sensor encontrado: {start_handle}-{end_handle}")
    
    def _handle_service_done(self, data):
        """Descoberta de serviços concluída"""
        if self.service_discovered:
            print("Descobrindo características...")
            start_handle, end_handle = self.service_handles
            self.ble.gattc_discover_characteristics(
                self.conn_handle, start_handle, end_handle, ANALOG_VALUE_CHAR_UUID
            )
        else:
            print("Serviço sensor não encontrado!")
    
    def _handle_characteristic_result(self, data):
        """Resultado da descoberta de características"""
        conn_handle, end_handle, value_handle, properties, uuid = data
        
        # Verifica se é a característica alvo
        if bluetooth.UUID(uuid) == ANALOG_VALUE_CHAR_UUID:
            self.char_handle = value_handle
            self.char_discovered = True
            print(f"Característica encontrada: handle {value_handle}")
    
    def _handle_characteristic_done(self, data):
        """Descoberta de características concluída"""
        if self.char_discovered:
            print("Descobrindo descritores...")
            self.ble.gattc_discover_descriptors(
                self.conn_handle, self.char_handle, self.char_handle + 2
            )
        else:
            print("Característica não encontrada!")
    
    def _handle_descriptor_result(self, data):
        """Resultado da descoberta de descritores"""
        conn_handle, dsc_handle, uuid = data
        
        # Verifica se é o CCCD
        if bluetooth.UUID(uuid) == _CCCD_UUID:
            self.cccd_handle = dsc_handle
            print(f"CCCD encontrado: handle {dsc_handle}")
            print("Habilitando notificações...")
            
            try:
                self.ble.gattc_write(
                    conn_handle, dsc_handle, 
                    struct.pack('<h', _NOTIFY_ENABLE), 1
                )
            except Exception as e:
                print(f"Erro ao habilitar notificações: {e}")
    
    def _handle_read_result(self, data):
        """Resultado de leitura"""
        conn_handle, value_handle, char_data = data
        
        if value_handle == self.char_handle:
            if len(char_data) >= 2:
                analog_value = struct.unpack('<H', char_data[:2])[0]
                print(f"Valor lido: {analog_value}")
            else:
                print(f"Dados: {bytes(char_data)}")
    
    def _handle_notify(self, data):
        """Notificação recebida"""
        conn_handle, value_handle, notify_data = data
        
        if value_handle == self.char_handle:
            if len(notify_data) >= 2:
                analog_value = struct.unpack('<H', notify_data[:2])[0]
                print(f"Notificação - Valor: {analog_value}")
            else:
                print(f"Notificação: {bytes(notify_data)}")
    
    def _handle_write_done(self, data):
        """Confirmação de escrita"""
        conn_handle, value_handle, status = data
        if status == 0:
            print("Escrita OK")
        else:
            print(f"Erro na escrita: {status}")
    
    def scan_devices(self, duration_ms=None):
        """Inicia scan de dispositivos BLE"""
        if duration_ms is None:
            duration_ms = self.scan_duration
            
        try:
            print(f"Iniciando scan BLE por {duration_ms}ms...")
            self.scanning = True
            self.found_devices.clear()
            
            # Scan sem argumentos nomeados (v1.25.0)
            self.ble.gap_scan(duration_ms)
            return True
            
        except Exception as e:
            print(f"Erro ao iniciar scan: {e}")
            self.scanning = False
            return False
    
    def read_characteristic(self):
        """Lê valor da característica"""
        if self.connected and self.char_handle:
            try:
                print("Lendo característica...")
                self.ble.gattc_read(self.conn_handle, self.char_handle)
                return True
            except Exception as e:
                print(f"Erro na leitura: {e}")
                return False
        else:
            print("Não conectado ou característica não descoberta")
            return False
    
    def write_characteristic(self, data):
        """Escreve dados na característica"""
        if self.connected and self.char_handle:
            try:
                print(f"Escrevendo dados: {data}")
                self.ble.gattc_write(self.conn_handle, self.char_handle, data, 1)
                return True
            except Exception as e:
                print(f"Erro na escrita: {e}")
                return False
        else:
            print("Não conectado")
            return False
    
    def disconnect(self):
        """Desconecta do dispositivo"""
        if self.connected and self.conn_handle:
            try:
                self.ble.gap_disconnect(self.conn_handle)
                return True
            except Exception as e:
                print(f"Erro na desconexão: {e}")
                return False
        return False

# Função principal
def main():
    print("=== Cliente BLE Sensor ESP32 ===")
    print("MicroPython v1.25.0")
    
    # CONFIGURAÇÃO: Especifique o dispositivo alvo
    # Opção 1: Por MAC address específico (mais confiável)
    TARGET_MAC = None  # Exemplo: "84:ac:60:73:ef:dd" 
    
    # Opção 2: Por nome do dispositivo
    TARGET_NAME = "Sensor Multi-Connect"  # Exemplo: "ESP32_SENSOR"
    
    # Opção 3: Deixe None para ver lista e conectar manualmente
    
    # Cria cliente BLE
    client = BLESensorClient(target_mac=TARGET_MAC, device_name=TARGET_NAME)
    
    # Inicializa BLE
    if not client.init_ble():
        print("Falha na inicialização BLE")
        return
    
    try:
        # Inicia scan
        print("\n>>> Iniciando scan de dispositivos BLE...")
        if client.scan_devices():
            print("Aguardando scan ou conexão direta...")
            
            # Loop de scan - aguarda scan terminar OU dispositivo conectar
            timeout = time.ticks_ms() + client.scan_duration + 2000
            
            while time.ticks_diff(timeout, time.ticks_ms()) > 0:
                # Se não está mais escaneando (terminou ou foi interrompido)
                if not client.scanning:
                    break
                    
                # Se encontrou dispositivo alvo e está tentando conectar, sai do loop
                if client.target_device:
                    print("Dispositivo alvo encontrado - aguardando conexão...")
                    break
                    
                time.sleep(0.1)
            
            # Aguarda conexão e descoberta de características
            if client.target_device:
                print("Aguardando estabelecimento da conexão...")
                connection_timeout = time.ticks_ms() + 15000  # 15 segundos para conectar
                
                while time.ticks_diff(connection_timeout, time.ticks_ms()) > 0:
                    if client.connected and client.char_discovered:
                        break
                    time.sleep(0.1)
            
            # Verifica resultado
            if client.connected and client.char_discovered:
                print("\n" + "="*50)
                print("DISPOSITIVO CONECTADO E CONFIGURADO!")
                print("="*50)
                
                # Loop de operação
                contador = 0
                while client.connected:
                    contador += 1
                    print(f"\n--- Leitura {contador} ---")
                    client.read_characteristic()
                    time.sleep(3)  # Lê a cada 3 segundos
                    
                    # Para demonstração, para após 10 leituras
                    if contador >= 10:
                        print("Demonstração concluída - desconectando...")
                        break
                        
            elif not client.target_device:
                # Se não conectou automaticamente, mostra opções manuais
                print("\n" + "="*50)
                print("CONEXÃO MANUAL NECESSÁRIA")
                print("="*50)
                
                if client.found_devices:
                    client.listar_dispositivos()
                    
                    print("\nPara conectar manualmente, use:")
                    print("client.conectar_por_mac('MAC_ADDRESS')")
                    print("ou")
                    print("client.conectar_por_indice(NUMERO)")
                else:
                    print("Nenhum dispositivo encontrado!")
            else:
                print("Falha na conexão ou timeout durante estabelecimento da conexão")
        
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário")
    
    except Exception as e:
        print(f"Erro: {e}")
    
    finally:
        if client.connected:
            client.disconnect()
        print("Cliente BLE finalizado")

# Função auxiliar para uso interativo
def conectar_dispositivo(mac_address):
    """Função auxiliar para conectar rapidamente a um dispositivo específico"""
    client = BLESensorClient(target_mac=mac_address)
    
    if not client.init_ble():
        return None
        
    if client.scan_devices():
        time.sleep(client.scan_duration / 1000 + 1)  # Aguarda scan
        if client.target_device:
            return client
    
    return None

# Executa programa principal
if __name__ == "__main__":
    main()