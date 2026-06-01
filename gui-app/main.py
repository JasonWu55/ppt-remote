import secrets
import threading
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
from connector import Connector
from keyboard import press
import config

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')


def _make_tray_icon() -> Image.Image:
    img = Image.new('RGB', (64, 64), color=(30, 30, 200))
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, 56, 56], fill=(255, 255, 255))
    return img


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent: 'App'):
        super().__init__(parent)
        self._app = parent
        self.title('設定')
        self.geometry('380x160')
        self.resizable(False, False)
        self.grab_set()

        cfg = config.load()

        ctk.CTkLabel(self, text='Gateway URL').pack(pady=(20, 4))
        self._url_entry = ctk.CTkEntry(self, width=320)
        self._url_entry.insert(0, cfg['gateway_url'])
        self._url_entry.pack()

        btn = ctk.CTkFrame(self, fg_color='transparent')
        btn.pack(pady=16)
        ctk.CTkButton(btn, text='儲存', width=120,
                      command=self._save).grid(row=0, column=0, padx=8)
        ctk.CTkButton(btn, text='取消', width=120, fg_color='gray',
                      command=self.destroy).grid(row=0, column=1, padx=8)

    def _save(self):
        url = self._url_entry.get().strip()
        if url:
            config.save({'gateway_url': url})
            self._app.apply_settings()
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('PPT Remote')
        self.geometry('420x350')
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        self._tray: pystray.Icon | None = None
        self._connector: Connector | None = None
        self._mobile_count = 0
        self._cfg = config.load()

        self._build_ui()
        self._start_connector()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._status_label = ctk.CTkLabel(
            self, text='狀態：連線中...', text_color='orange')
        self._status_label.pack(pady=(20, 10))

        info = ctk.CTkFrame(self)
        info.pack(pady=6)

        ctk.CTkLabel(info, text='Room ID', text_color='gray').grid(
            row=0, column=0, padx=30)
        ctk.CTkLabel(info, text='PIN', text_color='gray').grid(
            row=0, column=1, padx=30)

        self._room_label = ctk.CTkLabel(
            info, text='----', font=ctk.CTkFont(size=28, weight='bold'))
        self._room_label.grid(row=1, column=0, padx=30, pady=6)

        self._pin_label = ctk.CTkLabel(
            info, text='----', font=ctk.CTkFont(size=28, weight='bold'))
        self._pin_label.grid(row=1, column=1, padx=30, pady=6)

        self._clients_label = ctk.CTkLabel(self, text='已連線手機：0 台')
        self._clients_label.pack(pady=4)

        self._gw_label = ctk.CTkLabel(
            self, text=f'Gateway：{self._cfg["gateway_url"]}',
            text_color='gray', font=ctk.CTkFont(size=11))
        self._gw_label.pack(pady=2)

        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame, text='重新產生 PIN', width=130,
            command=self._regenerate_pin
        ).grid(row=0, column=0, padx=5, pady=4)

        ctk.CTkButton(
            btn_frame, text='斷線重連', width=110,
            command=self._reconnect
        ).grid(row=0, column=1, padx=5, pady=4)

        ctk.CTkButton(
            btn_frame, text='設定', width=90,
            fg_color='gray', hover_color='#555',
            command=self._open_settings
        ).grid(row=0, column=2, padx=5, pady=4)

        self._copy_btn = ctk.CTkButton(
            btn_frame, text='複製連結', width=340,
            fg_color='#2d5a27', hover_color='#3a7a33',
            command=self._copy_link, state='disabled'
        )
        self._copy_btn.grid(row=1, column=0, columnspan=3, padx=5, pady=4)

    # ── Link ─────────────────────────────────────────────────────────────────

    def _copy_link(self):
        url = self._cfg['gateway_url']
        http_url = url.replace('wss://', 'https://').replace('ws://', 'http://')
        room = self._room_label.cget('text')
        pin = self._pin_label.cget('text')
        if room == '----' or pin == '----':
            return
        link = f'{http_url}/?room={room}&pin={pin}'
        self.clipboard_clear()
        self.clipboard_append(link)
        self._copy_btn.configure(text='已複製！')
        self.after(2000, lambda: self._copy_btn.configure(text='複製連結'))

    # ── Settings ─────────────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsDialog(self)

    def apply_settings(self):
        self._cfg = config.load()
        self._gw_label.configure(text=f'Gateway：{self._cfg["gateway_url"]}')
        self._reconnect_with_new_url()

    def _reconnect_with_new_url(self):
        if self._connector:
            self._connector.disconnect()
        self._room_label.configure(text='----')
        self._pin_label.configure(text='----')
        self._start_connector()

    # ── Connector lifecycle ──────────────────────────────────────────────────

    def _new_pin(self) -> str:
        return f'{secrets.randbelow(10000):04d}'

    def _start_connector(self, pin: str | None = None):
        if pin is None:
            pin = self._new_pin()
        self._connector = Connector(
            gateway_url=self._cfg['gateway_url'],
            pin=pin,
            on_room_ready=self._on_room_ready,
            on_key=self._on_key,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
            on_mobile_count=self._on_mobile_count,
        )
        self._connector.start()

    def _on_room_ready(self, room_id: str, pin: str):
        self.after(0, lambda: self._room_label.configure(text=room_id))
        self.after(0, lambda: self._pin_label.configure(text=pin))

    def _on_key(self, action: str):
        press(action)

    def _on_connect(self):
        self.after(0, lambda: self._status_label.configure(
            text='狀態：● 已連線 Gateway', text_color='green'))
        self.after(0, lambda: self._copy_btn.configure(state='normal'))

    def _on_mobile_count(self, count: int):
        self.after(0, lambda: self._clients_label.configure(
            text=f'已連線手機：{count} 台'))

    def _on_disconnect(self):
        self.after(0, lambda: self._status_label.configure(
            text='狀態：● 斷線，自動重連中...', text_color='red'))
        self.after(0, lambda: self._copy_btn.configure(state='disabled'))

    def _regenerate_pin(self):
        if self._connector:
            self._connector.disconnect()
        self._room_label.configure(text='----')
        self._pin_label.configure(text='----')
        self._start_connector()

    def _reconnect(self):
        if self._connector:
            pin = self._connector.pin
            self._connector.disconnect()
            self._start_connector(pin=pin)

    # ── Tray ────────────────────────────────────────────────────────────────

    def _on_close(self):
        self.withdraw()
        menu = pystray.Menu(
            pystray.MenuItem('顯示視窗', self._show_window, default=True),
            pystray.MenuItem('結束', self._quit),
        )
        self._tray = pystray.Icon(
            'PPT Remote', _make_tray_icon(), 'PPT Remote', menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _show_window(self, icon=None, item=None):
        if self._tray:
            self._tray.stop()
            self._tray = None
        self.after(0, self.deiconify)

    def _quit(self, icon=None, item=None):
        if self._tray:
            self._tray.stop()
        if self._connector:
            self._connector.disconnect()
        self.after(0, self.destroy)


if __name__ == '__main__':
    App().mainloop()
