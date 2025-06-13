"""
Programa principal - Cliente BLE ESP32 modular
Demonstração de uso da arquitetura modular
"""

import gc
import time
from ble_client import BLESensorClient
from utils import conectar_dispositivo, get_memory_info

def main():
    print("=== Cliente BLE ESP32 Modular ===")
    memory_info = get_memory_info()
    print(f"RAM inicial: {memory_info['free']} bytes")
    
    # Configuração otimizada
    config = {
        'scan_duration': 60000,
        'connection_timeout': 6000,
        'rssi_threshold': -100,
        'auto_reconnect': True,
        'max_retries': 8,
        'gc_interval': 6,
        'memory_threshold': 35000
    }
    
    # CONFIGURAÇÃO DO DISPOSITIVO ALVO
    TARGET_MAC = None # Defina o MAC do dispositivo alvo ou deixe None para descoberta
    TARGET_NAME = "ADC-Server" # Nome do dispositivo alvo, se conhecido
    
    client = BLESensorClient(
        target_mac=TARGET_MAC,
        device_name=TARGET_NAME,
        config=config
    )
    
    if not client.init_ble():
        print("Falha na inicialização")
        return
    
    try:
        print("\n>>> Iniciando scan modular...")
        if client.scan_devices():
            
            # Aguarda com timeout
            scan_timeout = time.ticks_ms() + config['scan_duration'] + 8000
            
            while time.ticks_diff(scan_timeout, time.ticks_ms()) > 0:
                if client.is_ready():
                    break
                
                if client.state_machine.state == 1:  # STATE_SCANNING
                    print(".", end="")
                
                time.sleep_ms(500)
            
            print()
            
            # Verifica resultado
            if client.is_ready():
                print("\n" + "="*40)
                print("CLIENTE MODULAR PRONTO!")
                print("="*40)
                
                status = client.get_status()
                print(f"Estado: {status['state']}")
                print(f"Conectado a: {status['target_device']}")
                print(f"Memória: {status['memory_free']} bytes")
                print(f"Dispositivos analisados: {status['stats']['devices_analyzed']}")
                
                # Operação contínua
                print("\n>>> Operação contínua modular...")
                contador = 0
                
                while client.is_ready() and contador < 20:
                    contador += 1
                    print(f"\n--- Operação {contador} ---")
                    
                    if contador % 5 == 0:
                        status = client.get_status()
                        print(f"RAM: {status['memory_free']}b | "
                              f"Notif: {status['stats']['notifications']} | "
                              f"Erros: {status['stats']['errors']}")
                    
                    client.read_characteristic()
                    time.sleep(2)
                
                print("\nDemo modular concluída")
                
            else:
                print("\n" + "="*40)
                print("DISPOSITIVO ALVO NÃO ENCONTRADO")
                print("="*40)
                
                status = client.get_status()
                print(f"Dispositivos analisados: {status['stats']['devices_analyzed']}")
                print(f"Status: {status}")
        
    except KeyboardInterrupt:
        print("\nInterrompido")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        memory_info = get_memory_info()
        print(f"Finalizando... RAM: {memory_info['free']} bytes")
        client.disconnect()
        
        stats = client.get_status()['stats']
        print(f"Stats: Conexões: {stats['connections']}, "
              f"Dispositivos: {stats['devices_analyzed']}, "
              f"Notificações: {stats['notifications']}")

# Exemplo de uso da função utilitária
def exemplo_conexao_rapida():
    """Exemplo de conexão rápida usando utilitários"""
    print("=== Exemplo Conexão Rápida ===")
    
    client = conectar_dispositivo(
        mac_address="c0:5d:89:b1:1e:aa",
        device_name="ADC-Server",
        timeout_s=30
    )
    
    if client:
        print("Conectado com sucesso!")
        status = client.get_status()
        print(f"Status: {status}")
        
        # Algumas leituras
        for i in range(5):
            client.read_characteristic()
            time.sleep(1)
        
        client.disconnect()
    else:
        print("Falha na conexão")

if __name__ == "__main__":
    main()
    # exemplo_conexao_rapida()  # Descomente para testar