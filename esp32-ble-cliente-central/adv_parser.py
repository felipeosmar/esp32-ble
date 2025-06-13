"""
Parser de Advertisement Data otimizado
Processamento inline para ESP32
"""

import bluetooth

class AdvertisementParser:
    @staticmethod
    def extract_device_name(adv_data):
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
    
    @staticmethod
    def extract_service_uuids(adv_data):
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
    
    @staticmethod
    def is_target_device(addr_str, device_name, service_uuids, target_mac, target_name, target_service_uuid):
        """Identificação otimizada de dispositivo alvo - INLINE"""
        # 1. MAC específico (prioridade máxima)
        if target_mac and addr_str.lower() == target_mac.lower():
            return True
        
        # 2. Nome do dispositivo
        if (target_name and device_name and 
            target_name.lower() in device_name.lower()):
            return True
        
        # 3. UUID do serviço
        if service_uuids and target_service_uuid in service_uuids:
            return True
        
        return False