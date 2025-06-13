# main.py - VERSÃO FINAL COM SUPORTE A MÚLTIPLAS CONEXÕES

import bluetooth
import struct
import time
from machine import Pin, ADC
from ble_advertising import advertising_payload

# --- CONSTANTES DE EVENTOS BLUETOOTH ---
_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3

# --- DEFINIÇÃO DO SERVIÇO E CARACTERÍSTICA BLE ---
_SENSOR_SERVICE_UUID = bluetooth.UUID("c1a1b328-343c-4545-9aa4-a7453457d543")
_ANALOG_VALUE_CHAR_UUID = bluetooth.UUID("c1a2b328-343c-4545-9aa4-a7453457d543")
_ANALOG_VALUE_CHAR_FLAGS = bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY

class BLEAnalogSensor:
    def __init__(self, ble, name="ESP32-Sensor"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)

        char_tuple = (_ANALOG_VALUE_CHAR_UUID, _ANALOG_VALUE_CHAR_FLAGS)
        service_tuple = (_SENSOR_SERVICE_UUID, (char_tuple,))
        ((self._char_handle,),) = self._ble.gatts_register_services((service_tuple,))
        
        self._connections = set()

        # Usando a solução de Scan Response para nomes longos
        self._payload_adv = advertising_payload(services=[_SENSOR_SERVICE_UUID])
        self._payload_scan_resp = advertising_payload(name=name, is_scan_response=True)
        
        self._advertise()

    # Manipulador de interrupções para eventos BLE
    def _irq(self, event, data):
        # Um cliente (celular) se conectou
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("Novo dispositivo conectado, handle:", conn_handle)
            self._connections.add(conn_handle)
            
            # --- ALTERAÇÃO CRUCIAL AQUI ---
            # Continua a advertir para permitir que outros dispositivos se conectem.
            self._advertise()
        
        # O cliente se desconectou
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            print("Dispositivo desconectado, handle:", conn_handle)
            self._connections.remove(conn_handle)
            # Se não houver mais conexões, pode-se optar por parar de advertir,
            # mas é mais simples continuar advertindo sempre.
            self._advertise()
            
    # Envia o valor do sensor para TODOS os clientes conectados
    def send_sensor_value(self, value):
        for conn_handle in self._connections:
            # Envia a notificação para cada conexão no nosso conjunto
            try:
                self._ble.gatts_write(self._char_handle, struct.pack('<H', value))
                self._ble.gatts_notify(conn_handle, self._char_handle)
            except OSError as e:
                # Pode ocorrer um erro se um cliente desconectar abruptamente
                print(f"Erro ao enviar para handle {conn_handle}: {e}")


    # Inicia o "advertising" (anúncio)
    def _advertise(self, interval_us=500000):
        print("Iniciando advertising...")
        self._ble.gap_advertise(
            interval_us, 
            adv_data=self._payload_adv, 
            resp_data=self._payload_scan_resp
        )

# --- PROGRAMA PRINCIPAL ---

# 1. Configuração do Hardware (ADC)
pino_analogico = Pin(34, Pin.IN)

adc = ADC(pino_analogico)
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

# 2. Configuração do Software (BLE)
ble = bluetooth.BLE()
sensor_ble = BLEAnalogSensor(ble, name="Sensor Multi-Connect")

# 3. Loop de Execução
print("ESP32 pronto. Aguardando conexões BLE...")
while True:
    try:
        valor_lido = adc.read()
        
        # Envia o valor para todos os clientes conectados
        if sensor_ble._connections:
            sensor_ble.send_sensor_value(valor_lido)
            print(f"Valor Lido: {valor_lido} | Enviando para {len(sensor_ble._connections)} dispositivo(s).")
        else:
            # Imprime apenas localmente se ninguém estiver conectado
            print(f"Valor Lido: {valor_lido} | Aguardando conexão...")

        time.sleep_ms(500) # Aumentei um pouco o tempo para facilitar a visualização

    except KeyboardInterrupt:
        print("Programa interrompido.")
        break