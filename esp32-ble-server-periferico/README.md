# ESP32 BLE ADC Server - Arquitetura Modular

## **Problema**
Código monolítico dificulta manutenção, teste e reutilização. No ESP32 com MicroPython, é crucial manter arquivos organizados devido às limitações de memória e facilitar debugging.

## **Solução**
Divisão em módulos especializados permitindo importação seletiva, economizando RAM e facilitando manutenção.

## **Estrutura dos Arquivos**

### `config.py` - Configurações Centralizadas
- **Função**: Centraliza todos os parâmetros configuráveis
- **Conteúdo**: Pinos ADC, intervalos de timing, configurações BLE
- **Vantagem**: Mudanças em um local só, fácil customização

### `adc_manager.py` - Gerenciamento ADC  
- **Função**: Leitura e processamento dos canais ADC
- **Recursos**: Média móvel, conversão de valores, buffer circular
- **Otimização**: Operações com inteiros, buffer fixo para economizar RAM

### `ble_handler.py` - Comunicação BLE
- **Função**: Formatação e transmissão via Bluetooth Low Energy  
- **Recursos**: Controle de conexão, formatação de mensagens, tratamento de erros
- **Otimização**: Mensagens limitadas, reconexão automática

### `utils.py` - Utilitários do Sistema
- **Função**: Debug, validação de dados, gestão de memória
- **Recursos**: Logs com timestamp, garbage collection, validação
- **Otimização**: Debug condicional, limpeza automática de memória

### `main.py` - Aplicação Principal
- **Função**: Coordenação de todos os módulos
- **Recursos**: Loop principal, tratamento de erros, encerramento limpo
- **Arquitetura**: Classe principal que integra todos os componentes

## **Vantagens da Modularização**

### **Manutenibilidade**
- Código especializado por função
- Fácil localização de bugs
- Modificações isoladas

### **Reutilização**
- Módulos independentes
- Pode usar ADCManager em outros projetos
- BLEHandler reutilizável

### **Otimização de Memória**
- Importação seletiva
- Garbage collection eficiente
- Buffers localizados

### **Debugging**
- Logs específicos por módulo
- Controle granular de debug
- Isolamento de problemas

## **Como Usar**

### **Configuração Básica**
1. Ajuste `config.py` conforme necessário
2. Execute `main.py` no ESP32
3. Conecte via BLE para receber dados

### **Personalização**
- Modifique `ADC_PINS` em `config.py` para outros pinos
- Ajuste `READ_INTERVAL_MS` para velocidade diferente
- Altere `DEBUG_ENABLED` para produção

### **Exemplo de Conexão**
```python
# Em outro dispositivo Python
import config
from adc_manager import ADCManager

adc = ADCManager()
dados = adc.read_channels()
print(dados)
```

## **Recursos Implementados**

### **Hardware**
- ✅ 3 canais ADC (GPIO32, 33, 34)
- ✅ Resolução 12 bits (0-4095)
- ✅ Range 0-3.3V
- ✅ Média móvel para reduzir ruído

### **Software**
- ✅ Comunicação BLE otimizada
- ✅ Gestão automática de memória
- ✅ Debug configurável
- ✅ Tratamento robusto de erros
- ✅ Reconexão automática BLE

### **Otimizações**
- ✅ Buffer circular fixo
- ✅ Operações com inteiros
- ✅ Garbage collection periódico
- ✅ Mensagens BLE compactas
- ✅ Validação de dados

## **Monitoramento**
- Debug com timestamp
- Status de conexão BLE
- Tempo de atividade (uptime)
- Uso de memória
- Valores raw e processados

## **Expansibilidade**
- Fácil adição de novos canais
- Suporte para outros protocolos (Wi-Fi, MQTT)
- Integração com sensores I2C/SPI
- Logging em arquivo SD
