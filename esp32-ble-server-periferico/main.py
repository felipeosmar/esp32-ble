# main.py - Aplicação principal ESP32 BLE ADC Server
"""
Aplicação principal que coordena a leitura de 3 canais ADC
e transmissão via Bluetooth Low Energy (BLE)
"""

import time
import gc
from adc_manager import ADCManager
from ble_handler import BLEHandler
from utils import SystemUtils, DataValidator
import config

class ESP32ADCServer:
    """Servidor principal ESP32 para leitura ADC e transmissão BLE"""
    
    def __init__(self):
        """Inicializa todos os componentes do sistema"""
        print(f"=== Inicializando {config.BLE_DEVICE_NAME} ===")
        
        # Inicializar componentes
        self.adc_manager = ADCManager()
        self.ble_handler = BLEHandler()
        self.utils = SystemUtils()
        
        # Variáveis de controle
        self.last_read = 0
        self.last_gc = 0
        self.running = True
        
        print("Sistema inicializado com sucesso!")
        print(f"Canais ADC: {self.adc_manager.get_channel_count()}")
        print(f"Intervalo de leitura: {config.READ_INTERVAL_MS}ms")
        print("-" * 40)
    
    def run(self):
        """Loop principal da aplicação"""
        print("Iniciando loop principal...")
        
        while self.running:
            try:
                current_time = time.ticks_ms()
                
                # Leitura periódica dos ADCs
                if time.ticks_diff(current_time, self.last_read) >= config.READ_INTERVAL_MS:
                    self._process_adc_readings(current_time)
                
                # Garbage collection periódico
                if time.ticks_diff(current_time, self.last_gc) >= config.GC_INTERVAL_MS:
                    self._perform_maintenance(current_time)
                
                # Delay para não sobrecarregar o CPU
                time.sleep_ms(config.MAIN_LOOP_DELAY_MS)
                
            except KeyboardInterrupt:
                print("\nInterrompido pelo usuário")
                self.shutdown()
                break
                
            except Exception as e:
                SystemUtils.print_debug(f"Erro no loop principal: {e}")
                time.sleep_ms(100)  # Pequena pausa em caso de erro
    
    def _process_adc_readings(self, current_time):
        """Processa leituras dos canais ADC"""
        try:
            # Ler os canais ADC
            analog_values = self.adc_manager.read_channels()
            
            # Validar dados
            if not DataValidator.validate_adc_data(analog_values):
                SystemUtils.print_debug("Dados ADC inválidos ignorados")
                return
            
            # Enviar via BLE se conectado
            if self.ble_handler.send_data(analog_values):
                # Debug detalhado
                SystemUtils.print_channel_data(analog_values)
            else:
                # Apenas log se não conectado
                if config.DEBUG_ENABLED:
                    SystemUtils.print_debug("Aguardando conexão BLE...", show_timestamp=False)
            
            self.last_read = current_time
            
        except Exception as e:
            SystemUtils.print_debug(f"Erro na leitura ADC: {e}")
    
    def _perform_maintenance(self, current_time):
        """Executa manutenção periódica do sistema"""
        try:
            # Garbage collection
            freed_memory = SystemUtils.perform_gc()
            
            # Log de status periodicamente
            if config.DEBUG_ENABLED:
                uptime = SystemUtils.format_uptime()
                connection_status = "Conectado" if self.ble_handler.is_connected() else "Desconectado"
                SystemUtils.print_debug(f"Status: {connection_status} | Uptime: {uptime}")
            
            self.last_gc = current_time
            
        except Exception as e:
            SystemUtils.print_debug(f"Erro na manutenção: {e}")
    
    def shutdown(self):
        """Encerra o sistema de forma limpa"""
        print("Encerrando sistema...")
        self.running = False
        
        try:
            self.ble_handler.disconnect()
            SystemUtils.perform_gc()
            print("Sistema encerrado com sucesso")
        except Exception as e:
            print(f"Erro no encerramento: {e}")

# Função principal
def main():
    """Função principal da aplicação"""
    try:
        server = ESP32ADCServer()
        server.run()
    except Exception as e:
        print(f"Erro crítico: {e}")
        # Tentar reiniciar o sistema
        gc.collect()
        time.sleep_ms(1000)

# Executar se for o arquivo principal
if __name__ == "__main__":
    main()