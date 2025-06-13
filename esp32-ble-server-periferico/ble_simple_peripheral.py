# ble_simple_peripheral.py - Implementação BLE nativa para ESP32
"""
Implementação BLE Peripheral usando apenas bibliotecas nativas do MicroPython
Substitui módulos externos para otimizar memória e compatibilidade
"""

import bluetooth
import struct
import time
from micropython import const

# Constantes BLE (otimizadas para memoria)
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)

# UUID para serviço UART customizado (128-bit)
_UART_UUID =    bluetooth.UUID('6E400000-B5A3-F393-E0A9-E50E24DCCA9E')
_UART_TX_UUID = bluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
_UART_RX_UUID = bluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')

# Configuração do serviço UART
_UART_SERVICE = (_UART_UUID, (
    (_UART_TX_UUID, bluetooth.FLAG_NOTIFY),
    (_UART_RX_UUID, bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE),
))

class BLESimplePeripheral:
    """Implementação simplificada de BLE Peripheral para ESP32"""
    
    def __init__(self, ble, name="ESP32-ADC"):
        """
        Inicializa o peripheral BLE
        
        Args:
            ble: Instância bluetooth.BLE()
            name: Nome do dispositivo BLE
        """
        self._ble = ble
        self._name = name
        self._conn_handle = None
        self._write_callback = None
        
        # Ativar BLE
        self._ble.active(True)
        self._ble.irq(self._irq_handler)
        
        # Registrar serviços
        self._register_services()
        
        # Iniciar advertising
        self._advertise()
        
        print(f"BLE Peripheral '{name}' inicializado")
    
    def _irq_handler(self, event, data):
        """Handler para eventos BLE"""
        if event == _IRQ_CENTRAL_CONNECT:
            # Cliente conectado
            conn_handle, addr_type, addr = data
            self._conn_handle = conn_handle
            print(f"Cliente BLE conectado: {self._format_addr(addr)}")
            
        elif event == _IRQ_CENTRAL_DISCONNECT:
            # Cliente desconectado
            conn_handle, addr_type, addr = data
            self._conn_handle = None
            print(f"Cliente BLE desconectado: {self._format_addr(addr)}")
            # Reiniciar advertising
            self._advertise()
            
        elif event == _IRQ_GATTS_WRITE:
            # Dados recebidos
            conn_handle, value_handle = data
            if self._write_callback:
                value = self._ble.gatts_read(value_handle)
                self._write_callback(value)
    
    def _register_services(self):
        """Registra os serviços BLE"""
        try:
            # Registrar serviço UART
            ((self._tx_handle, self._rx_handle),) = self._ble.gatts_register_services((_UART_SERVICE,))
            print("Serviços BLE registrados")
        except Exception as e:
            print(f"Erro ao registrar serviços: {e}")
    
    def _advertise(self, interval_us=500000):
        """
        Inicia advertising BLE
        
        Args:
            interval_us: Intervalo de advertising em microsegundos
        """
        try:
            # Payload do advertising (otimizado para memoria)
            name_bytes = self._name.encode('utf-8')[:10]  # Limitar nome
            
            # AD Type: Complete Local Name (0x09)
            adv_data = bytes([len(name_bytes) + 1, 0x09]) + name_bytes
            
            # Iniciar advertising
            self._ble.gap_advertise(interval_us, adv_data)
            print(f"Advertising iniciado: {self._name}")
            
        except Exception as e:
            print(f"Erro no advertising: {e}")
    
    def send(self, data):
        """
        Envia dados via BLE
        
        Args:
            data: String ou bytes para enviar
            
        Returns:
            bool: True se enviado com sucesso
        """
        if not self.is_connected():
            return False
        
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Limitar tamanho da mensagem (MTU BLE típico)
            if len(data) > 20:
                data = data[:20]
            
            # Enviar notificação
            self._ble.gatts_notify(self._conn_handle, self._tx_handle, data)
            return True
            
        except Exception as e:
            print(f"Erro ao enviar dados BLE: {e}")
            return False
    
    def is_connected(self):
        """
        Verifica se há cliente conectado
        
        Returns:
            bool: Status da conexão
        """
        return self._conn_handle is not None
    
    def on_write(self, callback):
        """
        Define callback para dados recebidos
        
        Args:
            callback: Função callback(data)
        """
        self._write_callback = callback
    
    def disconnect(self):
        """Desconecta cliente atual"""
        if self._conn_handle is not None:
            try:
                self._ble.gap_disconnect(self._conn_handle)
                self._conn_handle = None
                print("Cliente desconectado")
            except Exception as e:
                print(f"Erro ao desconectar: {e}")
    
    def stop(self):
        """Para o advertising e desativa BLE"""
        try:
            self._ble.gap_advertise(None)  # Para advertising
            self._ble.active(False)
            print("BLE desativado")
        except Exception as e:
            print(f"Erro ao parar BLE: {e}")
    
    def _format_addr(self, addr):
        """Formata endereço MAC para exibição"""
        return ':'.join(f'{b:02x}' for b in addr)
    
    def get_stats(self):
        """
        Retorna estatísticas da conexão
        
        Returns:
            dict: Estatísticas BLE
        """
        return {
            'name': self._name,
            'connected': self.is_connected(),
            'conn_handle': self._conn_handle,
            'tx_handle': getattr(self, '_tx_handle', None),
            'rx_handle': getattr(self, '_rx_handle', None)
        }
