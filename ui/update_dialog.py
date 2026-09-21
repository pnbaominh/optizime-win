import customtkinter as ctk
from tkinter import messagebox
from typing import Dict, Any
from ui.theme import (
    COLOR_BG_DARK, COLOR_CARD_BG, COLOR_BORDER,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER,
    COLOR_TEXT_WHITE, COLOR_TEXT_MUTED, COLOR_TEXT_DIM, FONT_FAMILY
)
from core.updater import download_and_install_update

class UpdateDialog(ctk.CTkToplevel):
    def __init__(self, parent, update_info: Dict[str, Any]):
        super().__init__(parent)
        self.update_info = update_info

        self.title("Bản Cập Nhật Mới - Windows Deep Optimizer")
        self.geometry("540x440")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)

        # Căn giữa màn hình và giữ trên cùng
        self.transient(parent)
        self.grab_set()

        self._init_ui()

    def _init_ui(self):
        # Header Box
        header_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        header_frame.pack(fill="x", padx=16, pady=(16, 12))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text=f"🚀 Phát hiện bản cập nhật mới: {self.update_info['latest_version']}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        title_lbl.pack(anchor="w", padx=14, pady=(12, 4))

        cur_lbl = ctk.CTkLabel(
            header_frame,
            text=f"Phiên bản hiện tại: {self.update_info['current_version']}  ➔  Phiên bản mới nhất: {self.update_info['latest_version']}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        )
        cur_lbl.pack(anchor="w", padx=14, pady=(0, 12))

        # Changelog / Release Notes Box
        cl_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        cl_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        cl_title = ctk.CTkLabel(
            cl_frame,
            text="📋 Nội dung bản cập nhật (Changelog):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        cl_title.pack(anchor="w", padx=12, pady=(10, 4))

        self.cl_text = ctk.CTkTextbox(
            cl_frame,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#090d16",
            text_color=COLOR_TEXT_WHITE,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=6
        )
        self.cl_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.cl_text.insert("1.0", self.update_info.get("changelog", "Không có thông tin chi tiết."))
        self.cl_text.configure(state="disabled")

        # Progress Area
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.status_lbl = ctk.CTkLabel(
            self.progress_frame,
            text="Sẵn sàng cập nhật tự động bằng 1 cú nhấp chuột.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.status_lbl.pack(anchor="w", pady=(0, 4))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, fg_color="#1e293b", progress_color=COLOR_PRIMARY)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(8, 16))

        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Để sau",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#334155",
            hover_color="#475569",
            width=100,
            height=34,
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_update = ctk.CTkButton(
            btn_frame,
            text="⚡ Cập Nhật Tự Động Ngay",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            width=200,
            height=34,
            command=self._start_update
        )
        self.btn_update.pack(side="right")

    def _start_update(self):
        download_url = self.update_info.get("download_url")
        if not download_url:
            messagebox.showerror(
                "Lỗi cập nhật",
                "Không tìm thấy file cài đặt đính kèm trong bản phát hành này. Vui lòng thử lại sau."
            )
            return

        self.btn_update.configure(state="disabled", text="Đang tải xuống...")
        self.btn_cancel.configure(state="disabled")

        def on_progress(downloaded, total, percent):
            mb_down = round(downloaded / (1024 * 1024), 1)
            mb_tot = round(total / (1024 * 1024), 1) if total > 0 else 0
            self.after(0, lambda: self._update_progress_ui(percent, mb_down, mb_tot))

        def on_complete():
            self.after(0, lambda: self.status_lbl.configure(
                text="Tải xong! Đang khởi động trình cài đặt để nâng cấp..."
            ))

        def on_error(err_msg):
            self.after(0, lambda: self._handle_error(err_msg))

        download_and_install_update(
            download_url,
            progress_callback=on_progress,
            completion_callback=on_complete,
            error_callback=on_error
        )

    def _update_progress_ui(self, percent: float, mb_down: float, mb_tot: float):
        self.progress_bar.set(percent / 100.0)
        self.status_lbl.configure(
            text=f"Đang tải bản cài đặt: {mb_down} MB / {mb_tot} MB ({percent:.1f}%)"
        )

    def _handle_error(self, err_msg: str):
        self.btn_update.configure(state="normal", text="Thử lại")
        self.btn_cancel.configure(state="normal")
        self.status_lbl.configure(text=f"Lỗi: {err_msg}", text_color="#ef4444")
        messagebox.showerror("Lỗi Cập Nhật", f"Không thể tải bản cập nhật:\n{err_msg}")
