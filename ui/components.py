import customtkinter as ctk
from typing import Callable
from core.tweak_base import Tweak
from ui.theme import (
    COLOR_CARD_BG, COLOR_BORDER, COLOR_PRIMARY, COLOR_SUCCESS,
    COLOR_WARNING, COLOR_TEXT_WHITE, COLOR_TEXT_MUTED, COLOR_TEXT_DIM,
    FONT_FAMILY
)

class TweakCard(ctk.CTkFrame):
    """Card hiển thị 1 tùy chọn tối ưu với switch toggle và nút xem giải thích."""
    def __init__(
        self,
        master,
        tweak: Tweak,
        on_toggle: Callable[[Tweak, bool], None],
        on_show_info: Callable[[Tweak], None],
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=8,
            **kwargs
        )
        self.tweak = tweak
        self.on_toggle = on_toggle
        self.on_show_info = on_show_info

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        # Trạng thái hiện tại
        is_applied = self.tweak.check()

        # Cột trái: Tên, Mô tả, Badge
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)

        # Dòng tiêu đề + badge
        title_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        title_row.pack(fill="x", anchor="w")

        title_label = ctk.CTkLabel(
            title_row,
            text=self.tweak.name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        title_label.pack(side="left", padx=(0, 10))

        # Badge đề xuất
        if self.tweak.is_recommended:
            badge_rec = ctk.CTkLabel(
                title_row,
                text="KHUYÊN DÙNG",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                text_color="#38bdf8",
                fg_color="#082f49",
                corner_radius=4,
                padx=6,
                pady=2
            )
            badge_rec.pack(side="left", padx=4)

        # Badge trạng thái thực tế
        self.status_badge = ctk.CTkLabel(
            title_row,
            text="ĐÃ BẬT" if is_applied else "MẶC ĐỊNH",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=COLOR_SUCCESS if is_applied else COLOR_WARNING,
            fg_color="#064e3b" if is_applied else "#451a03",
            corner_radius=4,
            padx=6,
            pady=2
        )
        self.status_badge.pack(side="left", padx=4)

        # Mô tả ngắn
        desc_label = ctk.CTkLabel(
            info_frame,
            text=self.tweak.description,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=600
        )
        desc_label.pack(fill="x", anchor="w", pady=(4, 4))

        # Nút xem giải thích chi tiết
        info_btn = ctk.CTkButton(
            info_frame,
            text="ℹ️ Xem cơ chế hoạt động & giải thích chi tiết",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_PRIMARY,
            fg_color="transparent",
            hover=False,
            anchor="w",
            cursor="hand2",
            command=lambda: self.on_show_info(self.tweak)
        )
        info_btn.pack(anchor="w", pady=(0, 0))

        # Cột phải: Switch Toggle
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="e", padx=16, pady=12)

        self.switch_var = ctk.BooleanVar(value=is_applied)
        self.switch = ctk.CTkSwitch(
            right_frame,
            text="",
            variable=self.switch_var,
            onvalue=True,
            offvalue=False,
            progress_color=COLOR_SUCCESS,
            button_color=COLOR_TEXT_WHITE,
            button_hover_color="#e2e8f0",
            command=self._handle_switch_click,
            width=50
        )
        self.switch.pack(side="right")

    def _handle_switch_click(self):
        new_val = self.switch_var.get()
        self.switch.configure(state="disabled")
        self.status_badge.configure(
            text="ĐANG XỬ LÝ...",
            text_color="#38bdf8",
            fg_color="#082f49"
        )
        self.on_toggle(self.tweak, new_val)

    def refresh_state(self):
        """Đọc lại trạng thái thực tế và cập nhật giao diện."""
        try:
            is_applied = self.tweak.check()
            self.switch_var.set(is_applied)
            self.switch.configure(state="normal")
            self.status_badge.configure(
                text="ĐÃ BẬT" if is_applied else "MẶC ĐỊNH",
                text_color=COLOR_SUCCESS if is_applied else COLOR_WARNING,
                fg_color="#064e3b" if is_applied else "#451a03"
            )
        except Exception:
            self.switch.configure(state="normal")


class StatBox(ctk.CTkFrame):
    """Hộp thống kê KPI trên bảng điều khiển."""
    def __init__(self, master, title: str, value: str, subtext: str, badge_color: str = COLOR_PRIMARY, **kwargs):
        super().__init__(
            master,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=8,
            **kwargs
        )
        self.pack_propagate(False)

        title_lbl = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        title_lbl.pack(anchor="w", padx=16, pady=(12, 4))

        self.val_lbl = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        self.val_lbl.pack(anchor="w", padx=16)

        self.sub_lbl = ctk.CTkLabel(
            self,
            text=subtext,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=badge_color
        )
        self.sub_lbl.pack(anchor="w", padx=16, pady=(2, 10))

    def update_value(self, value: str, subtext: str = None):
        self.val_lbl.configure(text=value)
        if subtext:
            self.sub_lbl.configure(text=subtext)
