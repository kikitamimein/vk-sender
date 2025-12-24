import vk_api
import time
import asyncio
import requests
from typing import List, Dict, Any, Callable

class VKManager:
    def __init__(self, token: str, group_id: int):
        self.token = token
        self.group_id = group_id
        self.vk_session = vk_api.VkApi(token=token)
        self.vk = self.vk_session.get_api()
        self.is_running = False

    async def upload_photo(self, file_path: str) -> str:
        """Uploads a local photo to VK and returns its attachment ID."""
        try:
            # 1. Get upload server
            upload_server = self.vk.photos.getMessagesUploadServer(peer_id=0, group_id=self.group_id)
            upload_url = upload_server['upload_url']
            
            # 2. Upload file
            with open(file_path, 'rb') as f:
                files = {'photo': f}
                response = requests.post(upload_url, files=files).json()
            
            # 3. Save photo
            saved_photo = self.vk.photos.saveMessagesPhoto(
                photo=response['photo'],
                server=response['server'],
                hash=response['hash']
            )[0]
            
            return f"photo{saved_photo['owner_id']}_{saved_photo['id']}"
        except Exception as e:
            print(f"Error uploading photo: {e}")
            return ""

    async def fetch_conversations(self) -> List[Dict[str, Any]]:
        """Fetches all conversations for the group."""
        conversations = []
        offset = 0
        count = 200
        
        try:
            while True:
                response = self.vk.messages.getConversations(
                    group_id=self.group_id,
                    offset=offset,
                    count=count,
                    filter="all"
                )
                items = response.get('items', [])
                if not items:
                    break
                
                for item in items:
                    peer = item['conversation']['peer']
                    if peer['type'] == 'user':
                        # Fetch user info for better display
                        user_id = peer['id']
                        conversations.append({
                            'id': user_id,
                            'last_message_date': item['last_message']['date'],
                            'last_message_text': item['last_message'].get('text', '')
                        })
                
                offset += count
                if offset >= response.get('count', 0):
                    break
            
            return conversations
        except Exception as e:
            print(f"Error fetching conversations: {e}")
            return []

    async def get_user_info(self, user_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Fetches user info (name, etc.) for a list of user IDs."""
        try:
            users = self.vk.users.get(user_ids=user_ids)
            return {u['id']: u for u in users}
        except Exception as e:
            print(f"Error fetching user info: {e}")
            return {}

    async def send_message(self, user_id: int, message: str, attachment: str = "") -> bool:
        """Sends a message to a specific user with optional attachments."""
        try:
            params = {
                "peer_id": user_id,
                "message": message,
                "random_id": int(time.time() * 1000),
                "group_id": self.group_id
            }
            if attachment:
                params["attachment"] = attachment
                
            self.vk.messages.send(**params)
            return True
        except Exception as e:
            print(f"Error sending message to {user_id}: {e}")
            return False

    async def mailing_loop(
        self, 
        user_ids: List[int], 
        message: str, 
        interval: float, 
        on_progress: Callable[[int, int, str], None],
        test_mode: bool = False,
        attachment: str = ""
    ):
        """Main mailing loop with progress updates and test mode."""
        self.is_running = True
        total = len(user_ids)
        
        for i, user_id in enumerate(user_ids):
            if not self.is_running:
                on_progress(i, total, f"Остановлено пользователем.")
                break
            
            if test_mode:
                success = True
                status = "Тест ОК (сообщение не отправлено)"
            else:
                success = await self.send_message(user_id, message, attachment=attachment)
                status = "Успешно" if success else "Ошибка"
            
            on_progress(i + 1, total, f"Пользователь {user_id}: {status}")
            
            if i < total - 1:
                await asyncio.sleep(interval)
        
        self.is_running = False
        on_progress(total, total, "Рассылка завершена.")

    async def filter_users(
        self, 
        conversations: List[Dict[str, Any]], 
        filter_type: str, 
        min_days: int = 0,
        max_days: int = 365,
        limit: int = 0
    ) -> List[int]:
        """Filters users based on the selected category and range."""
        filtered_ids = []
        now = time.time()
        
        for conv in conversations:
            user_id = conv['id']
            last_date = conv['last_message_date']
            days_ago = (now - last_date) / 86400
            
            if filter_type == "activity":
                if min_days <= days_ago <= max_days:
                    filtered_ids.append(user_id)
            elif filter_type == "all":
                filtered_ids.append(user_id)
        
        # Apply limit if specified
        if limit > 0:
            filtered_ids = filtered_ids[:limit]
                
        return filtered_ids

    def stop(self):
        self.is_running = False
