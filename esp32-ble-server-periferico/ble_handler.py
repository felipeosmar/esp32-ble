# ble_handler.py - Gerenciamento da comunicação BLE
"""
Módulo responsável pela comunicação Bluetooth Low Energy
Formatação e envio de dados via BLE usando implementação nativa
"""

import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
import config

class BLEHandler:
    """Gerenciador da comunicação BLE"""
    
    def __init__(self):
        """Inicializa o BLE peripheral"""
        self.ble = bluetooth.BLE()
        self.peripheral = BLESimplePeripheral(self.ble, config.BLE_DEVICE_NAME)
        self.connection_status = False
        
        print(f"BLE Handler inicializado - Device: {config.BLE_DEVICE_NAME}")
    
    def is_connected(self):
        """
        Verifica se há cliente conectado
        
        Returns:
            bool: Status da conexão
        """
        try:
            return self.peripheral.is_connected()
        except:
            return False
    
    def format_message(self, analog_data):
        """
        Formata dados ADC para transmissão BLE
        Formato: "ADC:C1=1.25V;C2=2.30V;C3=0.85V;"
        
        Args:
            analog_data (list): Lista com dados dos canais ADC
            
        Returns:
            str: Mensagem formatada para BLE
        """
        msg = "ADC:"
        
        for data in analog_data:
            msg += f"C{data['channel']}={data['voltage']}V;"
        
        # Limitar tamanho da mensagem para otimizar BLE
        return msg[:config.BLE_MESSAGE_MAX_LENGTH]
    
    def send_data(self, analog_data):
        """
        Envia dados via BLE se conectado
        
        Args:
            analog_data (list): Dados dos canais ADC
            
        Returns:
            bool: True se enviado com sucesso
        """
        if not self.is_connected():
            return False
        
        try:
            message = self.format_message(analog_data)
            self.peripheral.send(message)
            
            if config.DEBUG_ENABLED:
                print(f"BLE Enviado: {message}")
            
            return True
            
        except Exception as e:
            print(f"Erro BLE: {e}")
            return False
    
    def get_connection_info(self):
        """
        Retorna informações da conexão
        
        Returns:
            dict: Informações da conexão BLE
        """
        return {
            'connected': self.is_connected(),
            'device_name': config.BLE_DEVICE_NAME,
            'max_message_length': config.BLE_MESSAGE_MAX_LENGTH
        }
    
    def disconnect(self):
        """Desconecta cliente BLE"""
        try:
            if hasattr(self.peripheral, 'disconnect'):
                self.peripheral.disconnect()
                print("Cliente BLE desconectado")
        except Exception as e:
            print(f"Erro ao desconectar: {e}")
    
    def reset_connection(self):
        """Reinicia a conexão BLE"""
        try:
            self.disconnect()
            self.ble = bluetooth.BLE()
            self.peripheral = BLESimplePeripheral(self.ble)
            print("Conexão BLE reiniciada")
        except Exception as e:
            print(f"Erro ao reiniciar BLE: {e}")
