import bluetooth
import time
import gc
from micropython import const

# Configurações otimizadas
SCAN_TIMEOUT = const(30000)  # 30s máximo
RSSI_MIN = const(-80)        # RSSI mínimo aceitável
TARGET_NAME = "ESP32_Server"  # Nome do dispositivo alvo
TARGET_MAC = None            # MAC específico (opcional)

class BLEClientTargeted:
    def __init__(self, target_name, target_mac=None):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.target_name = target_name
        self.target_mac = target_mac
        self.target_found = False
        self.target_addr = None
        self.target_addr_type = None
        self.connection = None
        
    def _irq(self, event, data):
        if event == bluetooth._IRQ_SCAN_RESULT:
            addr_type, addr, connectable, rssi, adv_data = data
            
            # Filtro RSSI imediato - descarta se muito fraco
            if rssi < RSSI_MIN:
                return
                
            # Análise inline do dispositivo
            if self._is_target_device(addr, adv_data, rssi):
                print(f">>> ALVO ENCONTRADO! <<<")
                print(f"MAC: {bytes(addr).hex()}")
                print(f"RSSI: {rssi}dBm")
                
                # Salvar dados do alvo
                self.target_addr = addr
                self.target_addr_type = addr_type
                self.target_found = True
                
                # PARAR scan imediatamente
                self.ble.gap_scan(None)
                print("Scan interrompido - conectando...")
                
        elif event == bluetooth._IRQ_SCAN_DONE:
            if not self.target_found:
                print("Scan concluído - alvo não encontrado")
                
        elif event == bluetooth._IRQ_PERIPHERAL_CONNECT:
            conn_handle, addr_type, addr = data
            print(f"Conectado ao alvo: {bytes(addr).hex()}")
            self.connection = conn_handle
            
        elif event == bluetooth._IRQ_PERIPHERAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            print("Desconectado do alvo")
            self.connection = None
            
    def _is_target_device(self, addr, adv_data, rssi):
        """Análise inline - libera memória imediatamente"""
        
        # Verificar MAC específico se definido
        if self.target_mac:
            addr_hex = bytes(addr).hex()
            if addr_hex.lower() == self.target_mac.lower():
                return True
                
        # Decodificar advertising data inline
        device_name = self._decode_name(adv_data)
        
        # Log de debug compacto
        print(f"Analisando: {bytes(addr).hex()[:8]}... "
              f"RSSI:{rssi} Nome:'{device_name}'")
        
        # Verificar nome do dispositivo
        if device_name and self.target_name.lower() in device_name.lower():
            return True
            
        # Não é o alvo - memória liberada automaticamente
        return False
        
    def _decode_name(self, adv_data):
        """Decodifica nome do advertising data sem armazenar"""
        try:
            i = 0
            while i < len(adv_data):
                length = adv_data[i]
                if length == 0:
                    break
                    
                ad_type = adv_data[i + 1]
                # Tipo 0x09 = Complete Local Name
                # Tipo 0x08 = Shortened Local Name
                if ad_type in (0x08, 0x09):
                    name_bytes = adv_data[i + 2:i + 1 + length]
                    return name_bytes.decode('utf-8')
                    
                i += 1 + length
                
        except Exception:
            pass
        return None
        
    def scan_for_target(self):
        """Scan otimizado que para ao encontrar o alvo"""
        print(f"=== Procurando por '{self.target_name}' ===")
        print(f"RAM disponível: {gc.mem_free()} bytes")
        
        self.ble.irq(self._irq)
        self.target_found = False
        
        # Iniciar scan
        self.ble.gap_scan(SCAN_TIMEOUT, 30000, 30000, True)
        
        # Aguardar resultado
        start_time = time.ticks_ms()
        while not self.target_found and time.ticks_diff(time.ticks_ms(), start_time) < SCAN_TIMEOUT:
            time.sleep_ms(100)
            
        if self.target_found:
            return True
        else:
            self.ble.gap_scan(None)  # Garantir parada
            return False
            
    def connect_to_target(self):
        """Conecta ao dispositivo alvo encontrado"""
        if not self.target_found:
            print("Erro: Nenhum alvo encontrado para conectar")
            return False
            
        try:
            print("Iniciando conexão...")
            self.ble.gap_connect(self.target_addr_type, self.target_addr)
            
            # Aguardar conexão (timeout 10s)
            timeout = 10000
            start = time.ticks_ms()
            
            while not self.connection and time.ticks_diff(time.ticks_ms(), start) < timeout:
                time.sleep_ms(100)
                
            if self.connection:
                print("Conexão estabelecida com sucesso!")
                return True
            else:
                print("Timeout na conexão")
                return False
                
        except Exception as e:
            print(f"Erro na conexão: {e}")
            return False

# Uso otimizado
def main():
    print("=== Cliente BLE Targetado ESP32 ===")
    gc.collect()
    
    # Configurar alvo
    client = BLEClientTargeted(
        target_name="ESP32_Server",  # Nome do seu dispositivo
        target_mac=None              # MAC específico (opcional)
    )
    
    # Scan otimizado
    if client.scan_for_target():
        print(f"RAM após scan: {gc.mem_free()} bytes")
        
        # Conectar ao alvo
        if client.connect_to_target():
            print("Pronto para comunicação!")
            # Aqui continua sua lógica de comunicação...
        else:
            print("Falha na conexão")
    else:
        print("Dispositivo alvo não encontrado")

if __name__ == "__main__":
    main()