import flet as ft
import asyncio
import os
import time
import json
from vk_logic import VKManager

# Constants for styling - Cleaner, more stable palette
BG_COLOR = "#121212"
SURFACE_COLOR = "#1E1E1E"
ACCENT_COLOR = "#007AFF"  # Classic Blue
TEXT_COLOR = "#FFFFFF"
SECONDARY_TEXT = "#B0B0B0"
CONFIG_FILE = "config.json"

class VKSenderApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.vk_manager = None
        self.setup_page()
        self.init_ui_components()
        self.build_layout()
        
        # Initialize API on startup
        self.auto_init_api()

    def setup_page(self):
        self.page.title = " "
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = BG_COLOR
        self.page.padding = 20
        self.page.window_width = 1000
        self.page.window_height = 750
        self.page.update()

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {}

    def save_settings(self, token, group_id):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"vk_token": token, "vk_group_id": group_id}, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def auto_init_api(self):
        settings = self.load_settings()
        token = settings.get("vk_token")
        group_id = settings.get("vk_group_id")
        
        if token and group_id:
            try:
                self.vk_manager = VKManager(token, int(group_id))
                self.token_input.value = token
                self.group_id_input.value = str(group_id)
                self.log("API автоматически инициализировано из файла.")
            except Exception as e:
                self.log(f"Ошибка авто-инициализации: {e}")
        else:
            self.log("Настройки API не найдены. Пожалуйста, настройте их.")

    def init_ui_components(self):
        # File Picker
        self.file_picker = ft.FilePicker(on_result=self.on_file_result)
        self.page.overlay.append(self.file_picker)
        self.selected_file_path = None

        # API Settings
        self.token_input = ft.TextField(
            label="VK Access Token", 
            password=True, 
            can_reveal_password=True, 
            border_color=ACCENT_COLOR,
            text_size=14
        )
        self.group_id_input = ft.TextField(
            label="ID Группы", 
            border_color=ACCENT_COLOR,
            text_size=14
        )
        
        # Mailing Message
        self.message_input = ft.TextField(
            label="Текст рассылки",
            multiline=True,
            min_lines=10,
            max_lines=12,
            border_color="#333333",
            focused_border_color=ACCENT_COLOR,
            hint_text="Введите текст сообщения здесь...",
            text_size=14
        )

        # Attachment Input
        self.attachment_input = ft.TextField(
            label="Вложения (ID из ВК)",
            border_color="#333333",
            focused_border_color=ACCENT_COLOR,
            hint_text="Пример: photo-123456_789012",
            text_size=14
        )

        # Local File Upload
        self.file_info_text = ft.Text("Файл не выбран", size=12, color=SECONDARY_TEXT)
        self.select_file_button = ft.OutlinedButton(
            "Выбрать файл с ПК",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=lambda _: self.file_picker.pick_files(),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )
        self.clear_file_button = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_color="#CF6679",
            tooltip="Убрать файл",
            visible=False,
            on_click=self.reset_file
        )

        # Interval Settings
        self.interval_slider = ft.Slider(
            min=1, max=60, divisions=59, 
            label="{value} сек", value=3,
            active_color=ACCENT_COLOR
        )
        
        # Categorization
        self.filter_dropdown = ft.Dropdown(
            label="Категория",
            options=[
                ft.dropdown.Option("all", "Все пользователи"),
                ft.dropdown.Option("activity", "По активности (дни)"),
            ],
            value="all",
            on_change=self.on_filter_change,
            border_color="#333333"
        )

        # New Filters: Day Range
        self.min_days_input = ft.TextField(
            label="Мин. дней", 
            value="0", 
            width=100, 
            visible=False,
            border_color="#333333",
            text_size=14
        )
        self.max_days_input = ft.TextField(
            label="Макс. дней", 
            value="365", 
            width=100, 
            visible=False,
            border_color="#333333",
            text_size=14
        )

        # Recipient Limit
        self.limit_input = ft.TextField(
            label="Лимит получателей (0 = все)", 
            value="0", 
            border_color="#333333",
            text_size=14
        )

        # Test Mode
        self.test_mode_checkbox = ft.Checkbox(
            label="Тестовый режим (без отправки)", 
            value=False,
            fill_color=ACCENT_COLOR
        )

        # Progress & Logs
        self.progress_bar = ft.ProgressBar(
            value=0, 
            color=ACCENT_COLOR, 
            bgcolor="#333333", 
            height=8, 
            border_radius=4
        )
        self.progress_text = ft.Text("Готов к работе", size=14, color=SECONDARY_TEXT)
        self.log_area = ft.ListView(expand=True, spacing=5, padding=10)
        
        # Buttons
        self.start_button = ft.ElevatedButton(
            "Начать рассылку",
            icon=ft.Icons.PLAY_ARROW,
            style=ft.ButtonStyle(
                color=TEXT_COLOR,
                bgcolor=ACCENT_COLOR,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=self.start_mailing
        )
        self.stop_button = ft.ElevatedButton(
            "Остановить",
            icon=ft.Icons.STOP,
            style=ft.ButtonStyle(
                color=TEXT_COLOR,
                bgcolor="#CF6679",
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=self.stop_mailing,
            disabled=True
        )

    def build_layout(self):
        # Sidebar
        sidebar = ft.Container(
            content=ft.Column([
                self.filter_dropdown,
                ft.Row([self.min_days_input, self.max_days_input], spacing=10),
                self.limit_input,
                self.test_mode_checkbox,
                ft.Divider(height=20, color="#333333"),
                ft.Text("Интервал (секунды)", size=14, color=SECONDARY_TEXT),
                self.interval_slider,
                ft.Divider(height=20, color="#333333"),
                ft.OutlinedButton(
                    "Настройки API", 
                    icon=ft.Icons.SETTINGS, 
                    on_click=self.show_settings,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                ),
            ], spacing=15),
            padding=20,
            width=300,
            bgcolor=SURFACE_COLOR,
            border_radius=12,
        )

        # Main Content
        main_content = ft.Container(
            content=ft.Column([
                self.message_input,
                # Local File Row (Now first)
                ft.Row([
                    self.select_file_button,
                    self.file_info_text,
                    self.clear_file_button
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                # VK Attachment Row
                self.attachment_input,
                ft.Row([self.start_button, self.stop_button], spacing=15),
                ft.Column([
                    self.progress_text,
                    self.progress_bar,
                ], spacing=5),
                ft.Container(
                    content=self.log_area,
                    expand=True,
                    bgcolor="#121212",
                    border_radius=8,
                    padding=5,
                    border=ft.border.all(1, "#333333")
                )
            ], spacing=20),
            expand=True,
            padding=20,
            bgcolor=SURFACE_COLOR,
            border_radius=12,
        )

        self.page.add(
            ft.Row([sidebar, main_content], expand=True, spacing=20)
        )
        
    def on_file_result(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.selected_file_path = e.files[0].path
            self.file_info_text.value = f"Файл: {e.files[0].name}"
            self.clear_file_button.visible = True
            self.page.update()

    def reset_file(self, e):
        self.selected_file_path = None
        self.file_info_text.value = "Файл не выбран"
        self.clear_file_button.visible = False
        self.page.update()

    def on_filter_change(self, e):
        is_activity = (self.filter_dropdown.value == "activity")
        self.min_days_input.visible = is_activity
        self.max_days_input.visible = is_activity
        self.page.update()

    def show_settings(self, e):
        # Load current values into inputs
        settings = self.load_settings()
        self.token_input.value = settings.get("vk_token") or ""
        self.group_id_input.value = str(settings.get("vk_group_id") or "")

        def save_settings_click(e):
            try:
                token = self.token_input.value
                group_id = int(self.group_id_input.value or 0)
                
                if self.save_settings(token, group_id):
                    self.vk_manager = VKManager(token, group_id)
                    settings_dialog.open = False
                    self.log("Настройки API сохранены в файл.")
                    self.page.update()
                else:
                    self.log("Ошибка при сохранении файла настроек.")
            except ValueError:
                self.log("Ошибка: ID группы должен быть числом.")

        settings_dialog = ft.AlertDialog(
            title=ft.Text("Настройки API"),
            content=ft.Column([
                self.token_input,
                self.group_id_input,
            ], tight=True, spacing=15),
            actions=[
                ft.TextButton("Сохранить", on_click=save_settings_click),
                ft.TextButton("Отмена", on_click=lambda _: self.close_dialog(settings_dialog))
            ]
        )
        self.page.open(settings_dialog)

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def log(self, message: str):
        self.log_area.controls.append(
            ft.Text(
                f"[{time.strftime('%H:%M:%S')}] {message}", 
                size=12, 
                color=SECONDARY_TEXT
            )
        )
        if len(self.log_area.controls) > 100:
            self.log_area.controls.pop(0)
        self.log_area.scroll_to(offset=-1, duration=100)
        self.page.update()

    async def start_mailing(self, e):
        if not self.vk_manager:
            self.log("Ошибка: Настройки API не заданы.")
            self.show_settings(None)
            return
        
        if not self.message_input.value and not self.attachment_input.value and not self.selected_file_path:
            self.log("Ошибка: Сообщение и вложения пусты.")
            return

        self.start_button.disabled = True
        self.stop_button.disabled = False
        
        # Handle local file upload
        final_attachment = self.attachment_input.value
        if self.selected_file_path:
            self.log(f"Загрузка файла {self.selected_file_path}...")
            self.page.update()
            uploaded_id = await self.vk_manager.upload_photo(self.selected_file_path)
            if uploaded_id:
                self.log(f"Файл успешно загружен: {uploaded_id}")
                if final_attachment:
                    final_attachment += f",{uploaded_id}"
                else:
                    final_attachment = uploaded_id
            else:
                self.log("Ошибка при загрузке файла.")
                self.reset_buttons()
                return

        self.log("Получение списка диалогов...")
        self.page.update()

        try:
            conversations = await self.vk_manager.fetch_conversations()
            if not conversations:
                self.log("Диалоги не найдены или произошла ошибка.")
                self.reset_buttons()
                return

            # Get filter parameters
            filter_type = self.filter_dropdown.value
            try:
                min_days = int(self.min_days_input.value or 0)
                max_days = int(self.max_days_input.value or 365)
                limit = int(self.limit_input.value or 0)
            except ValueError:
                self.log("Ошибка: Дни и Лимит должны быть числами.")
                self.reset_buttons()
                return

            user_ids = await self.vk_manager.filter_users(
                conversations, 
                filter_type, 
                min_days=min_days,
                max_days=max_days,
                limit=limit
            )

            if not user_ids:
                self.log("Нет пользователей, подходящих под фильтры.")
                self.reset_buttons()
                return

            test_mode = self.test_mode_checkbox.value
            mode_str = "(ТЕСТОВЫЙ РЕЖИМ)" if test_mode else ""
            self.log(f"Найдено {len(user_ids)} пользователей. Запуск рассылки {mode_str}...")
            
            def on_progress(current, total, status):
                self.progress_bar.value = current / total if total > 0 else 0
                self.progress_text.value = f"Прогресс: {current}/{total} - {status}"
                self.log(status)
                self.page.update()

            await self.vk_manager.mailing_loop(
                user_ids, 
                self.message_input.value, 
                self.interval_slider.value, 
                on_progress,
                test_mode=test_mode,
                attachment=final_attachment
            )
        except Exception as ex:
            self.log(f"Критическая ошибка: {ex}")
        
        self.reset_buttons()

    def reset_buttons(self):
        self.start_button.disabled = False
        self.stop_button.disabled = True
        self.page.update()

    def stop_mailing(self, e):
        if self.vk_manager:
            self.vk_manager.stop()
            self.log("Остановка рассылки...")

def main(page: ft.Page):
    VKSenderApp(page)

if __name__ == "__main__":
    ft.app(target=main)
