import flet as ft
import os
import threading
from datetime import datetime
from typing import List
from wifi_extractor import WifiExtractor, WifiProfile


class WifiDumpGUI:
    """Графический интерфейс для Wi-Fi Dump утилиты"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.extractor = WifiExtractor()
        self.profiles = []
        self.filtered_profiles = []
        
        # Настройка страницы
        self.page.title = "Wi-Fi Dump - Extractor"
        self.page.window_width = 1200
        self.page.window_height = 800
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        # Создание элементов UI
        self.create_ui()
    
    def create_ui(self):
        """Создание пользовательского интерфейса"""
        
        # Заголовок
        title = ft.Text(
            "Wi-Fi Credentials Extractor",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=ft.colors.BLUE_700
        )
        
        # Проверка прав администратора
        admin_status = ft.Container(
            content=ft.Row([
                ft.Icon(
                    ft.icons.SECURITY if self.extractor.is_admin else ft.icons.WARNING,
                    color=ft.colors.GREEN if self.extractor.is_admin else ft.colors.RED
                ),
                ft.Text(
                    "Administrator rights: " + ("✓ Available" if self.extractor.is_admin else "✗ Required"),
                    color=ft.colors.GREEN if self.extractor.is_admin else ft.colors.RED,
                    weight=ft.FontWeight.BOLD
                )
            ]),
            padding=10,
            border=ft.border.all(1, ft.colors.GREEN if self.extractor.is_admin else ft.colors.RED),
            border_radius=5,
            bgcolor=ft.colors.GREEN_50 if self.extractor.is_admin else ft.colors.RED_50
        )
        
        # Кнопки управления
        self.extract_btn = ft.ElevatedButton(
            "Extract Wi-Fi Profiles",
            icon=ft.icons.WIFI_FIND,
            on_click=self.extract_profiles,
            disabled=not self.extractor.is_admin
        )
        
        self.refresh_btn = ft.ElevatedButton(
            "Refresh",
            icon=ft.icons.REFRESH,
            on_click=self.refresh_profiles,
            disabled=True
        )
        
        # Фильтры
        self.filter_ssid = ft.TextField(
            label="Filter by SSID",
            hint_text="Enter SSID to filter...",
            on_change=self.apply_filters,
            width=250
        )
        
        self.filter_password = ft.Dropdown(
            label="Password filter",
            width=200,
            options=[
                ft.dropdown.Option("all", "All profiles"),
                ft.dropdown.Option("with_password", "With password"),
                ft.dropdown.Option("without_password", "Without password")
            ],
            value="all",
            on_change=self.apply_filters
        )
        
        # Статистика
        self.stats_text = ft.Text(
            "No profiles loaded",
            size=12,
            color=ft.colors.GREY_700
        )
        
        # Таблица профилей
        self.profiles_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("SSID", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Authentication", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Encryption", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Password", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD))
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5,
            data_row_min_height=60
        )
        
        # Скролл для таблицы
        self.table_container = ft.Container(
            content=ft.Column([
                self.profiles_table
            ], scroll=ft.ScrollMode.AUTO),
            height=400,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5
        )
        
        # Кнопки экспорта
        export_buttons = ft.Row([
            ft.ElevatedButton(
                "Export to TXT",
                icon=ft.icons.TEXT_SNIPPET,
                on_click=self.export_txt,
                disabled=True
            ),
            ft.ElevatedButton(
                "Export to CSV",
                icon=ft.icons.TABLE_CHART,
                on_click=self.export_csv,
                disabled=True
            ),
            ft.ElevatedButton(
                "Export to JSON",
                icon=ft.icons.DATA_OBJECT,
                on_click=self.export_json,
                disabled=True
            )
        ])
        
        self.export_buttons = export_buttons
        
        # Прогресс бар
        self.progress_bar = ft.ProgressBar(
            visible=False,
            color=ft.colors.BLUE,
            bgcolor=ft.colors.GREY_300
        )
        
        # Статус
        self.status_text = ft.Text(
            "Ready to extract Wi-Fi profiles",
            size=12,
            color=ft.colors.GREY_600
        )
        
        # Сборка интерфейса
        self.page.add(
            ft.Container(
                content=ft.Column([
                    title,
                    admin_status,
                    ft.Divider(),
                    
                    # Контролы
                    ft.Row([
                        self.extract_btn,
                        self.refresh_btn
                    ]),
                    
                    # Фильтры
                    ft.Row([
                        self.filter_ssid,
                        self.filter_password
                    ]),
                    
                    # Статистика
                    self.stats_text,
                    
                    # Таблица
                    self.table_container,
                    
                    # Экспорт
                    ft.Text("Export options:", weight=ft.FontWeight.BOLD),
                    export_buttons,
                    
                    # Прогресс и статус
                    self.progress_bar,
                    self.status_text
                ], spacing=10),
                padding=20
            )
        )
    
    def extract_profiles(self, e):
        """Извлечение профилей Wi-Fi"""
        self.show_progress("Extracting Wi-Fi profiles...")
        
        # Запуск в отдельном потоке
        threading.Thread(target=self._extract_profiles_thread, daemon=True).start()
    
    def _extract_profiles_thread(self):
        """Поток для извлечения профилей"""
        try:
            profiles = self.extractor.extract_profiles()
            self.profiles = profiles
            self.filtered_profiles = profiles
            
            # Обновляем UI в главном потоке
            self.page.run_thread(self._update_ui_after_extraction)
            
        except Exception as ex:
            self.page.run_thread(lambda: self.show_error(f"Error: {str(ex)}"))
    
    def _update_ui_after_extraction(self):
        """Обновление UI после извлечения"""
        self.update_table()
        self.update_stats()
        self.enable_export_buttons()
        self.refresh_btn.disabled = False
        self.hide_progress()
        self.status_text.value = f"Extracted {len(self.profiles)} profiles"
        self.page.update()
    
    def refresh_profiles(self, e):
        """Обновление списка профилей"""
        self.extract_profiles(e)
    
    def apply_filters(self, e):
        """Применение фильтров"""
        if not self.profiles:
            return
        
        # Фильтр по SSID
        ssid_filter = self.filter_ssid.value.strip() if self.filter_ssid.value else None
        
        # Фильтр по паролю
        password_filter = self.filter_password.value
        has_password = None
        if password_filter == "with_password":
            has_password = True
        elif password_filter == "without_password":
            has_password = False
        
        # Применяем фильтры
        self.filtered_profiles = self.extractor.filter_profiles(
            has_password=has_password,
            ssid_filter=ssid_filter
        )
        
        self.update_table()
        self.update_stats()
        self.page.update()
    
    def update_table(self):
        """Обновление таблицы профилей"""
        rows = []
        
        for profile in self.filtered_profiles:
            # Маскируем пароль
            password_display = profile.key
            if profile.key and profile.key not in ['No password saved', 'Not found']:
                password_display = '*' * len(profile.key)
            
            # Кнопка показа пароля
            show_password_btn = ft.IconButton(
                icon=ft.icons.VISIBILITY,
                tooltip="Show password",
                on_click=lambda e, p=profile: self.show_password(p)
            )
            
            # Кнопка копирования
            copy_btn = ft.IconButton(
                icon=ft.icons.COPY,
                tooltip="Copy password",
                on_click=lambda e, p=profile: self.copy_password(p)
            )
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(profile.ssid, size=12)),
                    ft.DataCell(ft.Text(profile.authentication, size=12)),
                    ft.DataCell(ft.Text(profile.encryption, size=12)),
                    ft.DataCell(ft.Text(password_display, size=12)),
                    ft.DataCell(ft.Row([show_password_btn, copy_btn]))
                ]
            )
            rows.append(row)
        
        self.profiles_table.rows = rows
    
    def update_stats(self):
        """Обновление статистики"""
        if not self.profiles:
            self.stats_text.value = "No profiles loaded"
            return
        
        stats = self.extractor.get_stats()
        filtered_count = len(self.filtered_profiles)
        
        self.stats_text.value = (
            f"Total: {stats['total_profiles']} | "
            f"Filtered: {filtered_count} | "
            f"With password: {stats['with_password']} | "
            f"Without password: {stats['without_password']}"
        )
    
    def show_password(self, profile: WifiProfile):
        """Показ пароля в диалоге"""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Password for {profile.ssid}"),
            content=ft.Column([
                ft.Text(f"SSID: {profile.ssid}"),
                ft.Text(f"Authentication: {profile.authentication}"),
                ft.Text(f"Encryption: {profile.encryption}"),
                ft.TextField(
                    label="Password",
                    value=profile.key,
                    read_only=True,
                    password=False,
                    width=300
                )
            ], height=200),
            actions=[
                ft.TextButton("Close", on_click=close_dialog)
            ]
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def copy_password(self, profile: WifiProfile):
        """Копирование пароля в буфер обмена"""
        if profile.key and profile.key not in ['No password saved', 'Not found']:
            self.page.set_clipboard(profile.key)
            self.show_snackbar(f"Password for {profile.ssid} copied to clipboard")
        else:
            self.show_snackbar(f"No password available for {profile.ssid}")
    
    def export_txt(self, e):
        """Экспорт в TXT"""
        self.export_file('txt')
    
    def export_csv(self, e):
        """Экспорт в CSV"""
        self.export_file('csv')
    
    def export_json(self, e):
        """Экспорт в JSON"""
        self.export_file('json')
    
    def export_file(self, format_type):
        """Общий метод экспорта"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wifi_profiles_{timestamp}.{format_type}"
        
        try:
            success = False
            if format_type == 'txt':
                success = self.extractor.export_to_txt(filename, self.filtered_profiles)
            elif format_type == 'csv':
                success = self.extractor.export_to_csv(filename, self.filtered_profiles)
            elif format_type == 'json':
                success = self.extractor.export_to_json(filename, self.filtered_profiles)
            
            if success:
                self.show_snackbar(f"Exported to {filename}")
            else:
                self.show_snackbar(f"Failed to export to {format_type.upper()}")
                
        except Exception as ex:
            self.show_snackbar(f"Export error: {str(ex)}")
    
    def enable_export_buttons(self):
        """Активация кнопок экспорта"""
        for btn in self.export_buttons.controls:
            btn.disabled = False
    
    def show_progress(self, message):
        """Показ прогресс бара"""
        self.progress_bar.visible = True
        self.status_text.value = message
        self.extract_btn.disabled = True
        self.page.update()
    
    def hide_progress(self):
        """Скрытие прогресс бара"""
        self.progress_bar.visible = False
        self.extract_btn.disabled = False
        self.page.update()
    
    def show_error(self, message):
        """Показ ошибки"""
        self.hide_progress()
        self.status_text.value = message
        self.status_text.color = ft.colors.RED
        self.page.update()
    
    def show_snackbar(self, message):
        """Показ уведомления"""
        snackbar = ft.SnackBar(
            content=ft.Text(message),
            action="OK"
        )
        self.page.snack_bar = snackbar
        snackbar.open = True
        self.page.update()


def main(page: ft.Page):
    """Главная функция для запуска приложения"""
    app = WifiDumpGUI(page)


if __name__ == "__main__":
    ft.app(target=main)
