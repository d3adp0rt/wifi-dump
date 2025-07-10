import subprocess
import re
import json
import csv
import os
import ctypes
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class WifiProfile:
    """Класс для представления профиля Wi-Fi"""
    ssid: str
    authentication: str
    encryption: str
    key: str
    key_type: str
    profile_type: str
    last_modified: str = ""
    
    def to_dict(self) -> Dict:
        """Преобразование в словарь для JSON экспорта"""
        return {
            'ssid': self.ssid,
            'authentication': self.authentication,
            'encryption': self.encryption,
            'key': self.key,
            'key_type': self.key_type,
            'profile_type': self.profile_type,
            'last_modified': self.last_modified
        }


class WifiExtractor:
    """Класс для извлечения Wi-Fi профилей из Windows"""
    
    def __init__(self):
        self.profiles: List[WifiProfile] = []
        self.is_admin = self._check_admin_rights()
    
    def _check_admin_rights(self) -> bool:
        """Проверка прав администратора"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def _run_command(self, command: str) -> str:
        """Выполнение команды и возврат результата"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='cp866'  # Кодировка для Windows консоли
            )
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error: {result.stderr}"
        except Exception as e:
            return f"Exception: {str(e)}"
    
    def _parse_profile_list(self, output: str) -> List[str]:
        """Парсинг списка профилей из вывода netsh с секцией 'Профили пользователей'"""
        profiles = []
        lines = output.split('\n')
        in_user_profiles_section = False

        for line in lines:
            line = line.strip()
            # Определяем начало секции профилей пользователей
            if line.startswith('Профили пользователей'):
                in_user_profiles_section = True
                continue

            # Если в секции, но встретили пустую строку или другую секцию — выходим из неё
            if in_user_profiles_section:
                if not line or line.startswith('Профили групповой политики'):
                    break
                # Ищем строку с профилем
                match = re.search(r'Все профили пользователей\s*:\s*(.+)', line)
                if match:
                    profiles.append(match.group(1).strip())

        return profiles
    
    def _parse_profile_details(self, output: str, profile_name: str) -> Optional[WifiProfile]:
        """Парсинг деталей профиля"""
        lines = output.split('\n')
        
        profile_data = {
            'ssid': profile_name,
            'authentication': 'Unknown',
            'encryption': 'Unknown',
            'key': 'Not found',
            'key_type': 'Unknown',
            'profile_type': 'Unknown',
            'last_modified': ''
        }
        
        for line in lines:
            line = line.strip()
            
            # Аутентификация
            if 'Authentication' in line or 'Проверка подлинности' in line:
                match = re.search(r':\s*(.+)', line)
                if match:
                    profile_data['authentication'] = match.group(1).strip()
            
            # Шифрование
            elif 'Cipher' in line or 'Шифр' in line:
                match = re.search(r':\s*(.+)', line)
                if match:
                    profile_data['encryption'] = match.group(1).strip()
            
            # Ключ безопасности
            elif 'Key Content' in line or 'Содержимое ключа' in line:
                match = re.search(r':\s*(.+)', line)
                if match:
                    key_content = match.group(1).strip()
                    if key_content and key_content != 'Absent':
                        profile_data['key'] = key_content
                    else:
                        profile_data['key'] = 'No password saved'
            
            # Тип ключа
            elif 'Key Type' in line or 'Тип ключа' in line:
                match = re.search(r':\s*(.+)', line)
                if match:
                    profile_data['key_type'] = match.group(1).strip()
            
            # Тип профиля
            elif 'Profile Type' in line or 'Тип профиля' in line:
                match = re.search(r':\s*(.+)', line)
                if match:
                    profile_data['profile_type'] = match.group(1).strip()
        
        return WifiProfile(**profile_data)
    
    def extract_profiles(self) -> List[WifiProfile]:
        """Основной метод извлечения профилей"""
        if not self.is_admin:
            raise PermissionError("Необходимы права администратора для доступа к Wi-Fi профилям")
        
        # Получаем список всех профилей
        profiles_output = self._run_command("netsh wlan show profiles")
        profile_names = self._parse_profile_list(profiles_output)
        print(profile_names)
        
        self.profiles = []
        
        for profile_name in profile_names:
            # Получаем детали каждого профиля
            details_command = f'netsh wlan show profile name="{profile_name}" key=clear'
            details_output = self._run_command(details_command)
            
            profile = self._parse_profile_details(details_output, profile_name)
            if profile:
                self.profiles.append(profile)
        
        return self.profiles
    
    def filter_profiles(self, has_password: bool = None, ssid_filter: str = None) -> List[WifiProfile]:
        """Фильтрация профилей"""
        filtered = self.profiles
        
        if has_password is not None:
            if has_password:
                filtered = [p for p in filtered if p.key and p.key != 'No password saved' and p.key != 'Not found']
            else:
                filtered = [p for p in filtered if not p.key or p.key == 'No password saved' or p.key == 'Not found']
        
        if ssid_filter:
            filtered = [p for p in filtered if ssid_filter.lower() in p.ssid.lower()]
        
        return filtered
    
    def export_to_txt(self, filename: str, profiles: List[WifiProfile] = None) -> bool:
        """Экспорт в текстовый файл"""
        if profiles is None:
            profiles = self.profiles
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=== Wi-Fi Profile Extractor Results ===\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total profiles: {len(profiles)}\n\n")
                
                for i, profile in enumerate(profiles, 1):
                    f.write(f"Profile #{i}\n")
                    f.write(f"SSID: {profile.ssid}\n")
                    f.write(f"Authentication: {profile.authentication}\n")
                    f.write(f"Encryption: {profile.encryption}\n")
                    f.write(f"Key: {profile.key}\n")
                    f.write(f"Key Type: {profile.key_type}\n")
                    f.write(f"Profile Type: {profile.profile_type}\n")
                    f.write("-" * 40 + "\n\n")
            
            return True
        except Exception as e:
            print(f"Error saving to TXT: {e}")
            return False
    
    def export_to_csv(self, filename: str, profiles: List[WifiProfile] = None) -> bool:
        """Экспорт в CSV файл"""
        if profiles is None:
            profiles = self.profiles
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['SSID', 'Authentication', 'Encryption', 'Key', 'Key Type', 'Profile Type']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for profile in profiles:
                    writer.writerow({
                        'SSID': profile.ssid,
                        'Authentication': profile.authentication,
                        'Encryption': profile.encryption,
                        'Key': profile.key,
                        'Key Type': profile.key_type,
                        'Profile Type': profile.profile_type
                    })
            
            return True
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False
    
    def export_to_json(self, filename: str, profiles: List[WifiProfile] = None) -> bool:
        """Экспорт в JSON файл"""
        if profiles is None:
            profiles = self.profiles
        
        try:
            data = {
                'generated': datetime.now().isoformat(),
                'total_profiles': len(profiles),
                'profiles': [profile.to_dict() for profile in profiles]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving to JSON: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Получение статистики по профилям"""
        total = len(self.profiles)
        with_password = len([p for p in self.profiles if p.key and p.key != 'No password saved' and p.key != 'Not found'])
        without_password = total - with_password
        
        auth_types = {}
        for profile in self.profiles:
            auth_type = profile.authentication
            auth_types[auth_type] = auth_types.get(auth_type, 0) + 1
        
        return {
            'total_profiles': total,
            'with_password': with_password,
            'without_password': without_password,
            'authentication_types': auth_types
        }
