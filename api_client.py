import requests
from typing import Optional, Dict, List
import json

class ApiClient:
    SUPER_USER = '+79953828610'
    
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url
        self.headers = {
            'x-api-key': api_token,
            'Content-Type': 'application/json'
        }
    
    def is_super_user(self, phone: str) -> bool:
        """Проверка является ли пользователь суперпользователем"""
        return phone == self.SUPER_USER
    
    def check_tenant(self, phone: str) -> Optional[Dict]:
        """Проверка и авторизация пользователя по номеру телефона"""
        try:
            if self.is_super_user(phone):
                return {'phone': phone, 'is_super_user': True}
            
            # Форматируем номер телефона
            phone = phone.replace('+', '')
            
            payload = {
                "phone": phone
            }
            
            response = requests.post(
                f"{self.base_url}/check-tenant",
                headers=self.headers,
                json=payload
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                # Добавляем дополнительную информацию для бота
                return {
                    'tenant_id': data.get('tenant_id'),
                    'phone': phone,
                    'name': 'Домофон',  # Добавляем стандартное имя
                    'id': str(data.get('tenant_id'))  # Преобразуем ID в строку
                }
            return None
        except Exception as e:
            print(f"Check tenant error: {e}")
            return None
    
    def get_tenant_domophones(self, phone: str) -> List[Dict]:
        """Получение списка доступных домофонов для пользователя"""
        try:
            # Форматируем номер телефона
            phone = phone.replace('+', '')
            
            # Получаем информацию о пользователе
            response = requests.post(
                f"{self.base_url}/check-tenant",
                headers=self.headers,
                json={"phone": phone}
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                tenant_id = data.get('tenant_id')
                # Возвращаем список с одним домофоном, используя tenant_id
                return [{
                    'name': f'Домофон #{tenant_id}',  # Добавляем номер домофона
                    'id': str(tenant_id),  # ID домофона как строка
                    'tenant_id': tenant_id
                }]
            return []
        except Exception as e:
            print(f"Get domophones error: {e}")
            return []
    
    def get_camera_snapshot(self, domophone_id: str, phone: str) -> Optional[bytes]:
        """Получение снимка с камеры домофона"""
        try:
            # Форматируем номер телефона
            phone = phone.replace('+', '')
            
            payload = {
                "phone": phone,
                "domophone_id": domophone_id
            }
            
            response = requests.post(
                f"{self.base_url}/get-snapshot",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.content
            print(f"Get snapshot response: {response.status_code}, {response.text}")
            return None
        except Exception as e:
            print(f"Get snapshot error: {e}")
            return None
    
    def open_domophone(self, domophone_id: str, phone: str) -> bool:
        """Открытие двери домофона"""
        try:
            # Форматируем номер телефона
            phone = phone.replace('+', '')
            
            payload = {
                "phone": phone,
                "domophone_id": domophone_id
            }
            
            response = requests.post(
                f"{self.base_url}/open-door",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code != 200:
                print(f"Open door response: {response.status_code}, {response.text}")
            return response.status_code == 200
        except Exception as e:
            print(f"Open door error: {e}")
            return False

    def grant_access(self, phone: str, domophone_id: str) -> bool:
        """Предоставление доступа пользователю (только для суперпользователя)"""
        try:
            response = requests.get(
                f"{self.base_url}/grant-access",
                params={
                    'phone': phone,
                    'domophone_id': domophone_id
                },
                headers=self.headers
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Grant access error: {e}")
            return False

    def revoke_access(self, phone: str, domophone_id: str) -> bool:
        """Отзыв доступа у пользователя (только для суперпользователя)"""
        try:
            response = requests.get(
                f"{self.base_url}/revoke-access",
                params={
                    'phone': phone,
                    'domophone_id': domophone_id
                },
                headers=self.headers
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Revoke access error: {e}")
            return False 