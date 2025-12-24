import asyncio
import time
from vk_logic import VKManager

async def test_logic():
    print("Starting mock test...")
    
    # Mock VKManager to avoid real API calls
    class MockVKManager(VKManager):
        def __init__(self):
            self.is_running = False
            self.group_id = 123
            
        async def fetch_conversations(self):
            return [
                {'id': 1, 'last_message_date': time.time() - 100, 'last_message_text': 'Hello!'},
                {'id': 2, 'last_message_date': time.time() - 1000000, 'last_message_text': 'Bye.'},
                {'id': 3, 'last_message_date': time.time() - 50, 'last_message_text': 'I want to buy something.'},
            ]
            
        async def send_message(self, user_id, message):
            print(f"Mock sending to {user_id}: {message}")
            await asyncio.sleep(0.1)
            return True

    manager = MockVKManager()
    
    # Test filtering with range
    convs = await manager.fetch_conversations()
    range_users = await manager.filter_users(convs, "activity", "", min_days=0, max_days=1)
    print(f"Users in range 0-1 days: {range_users}")
    assert len(range_users) == 2 # IDs 1 and 3
    
    # Test limit
    limited_users = await manager.filter_users(convs, "all", "", limit=1)
    print(f"Limited users (limit=1): {limited_users}")
    assert len(limited_users) == 1
    
    # Test mailing loop in TEST MODE
    print("Testing mailing loop in TEST MODE...")
    def on_progress(current, total, status):
        print(f"Progress: {current}/{total} - {status}")
        
    await manager.mailing_loop([1, 2, 3], "Test message", 0.1, on_progress, test_mode=True)
    print("Mock test finished successfully!")

if __name__ == "__main__":
    asyncio.run(test_logic())
