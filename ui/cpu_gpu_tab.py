"""
Module: ui/cpu_gpu_tab.py
Description: Giao diện Tab "⚡ Tối Ưu CPU & GPU" theo chuẩn Atomic Design.
             Hỗ trợ 10 tinh chỉnh phần cứng chuyên sâu (5 CPU + 5 GPU) với
             StatusBadge, Quick Apply, Revert và sao lưu Registry an toàn.
"""

from __future__ import annotations
import threading
from typing import Callable, Dict, Optional
import customtkinter as ctk

from core.contracts import TweakCategory, TweakDescriptor, TweakState
from core.cpu_optimizer import CpuOptimizerService
from core.gpu_optimizer import GpuOptimizerService
from core.registry_backup import RegistryBackupService
from ui.theme import (
    COLOR_CARD_BG,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS,
    COLOR_SUCCESS_HOVER,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_TEXT_WHITE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_DIM,
    FONT_FAMILY,
)


class StatusBadge(ctk.CTkLabel):
    """Badge hiển thị trạng thái tối ưu hóa trực quan."""

    STATE_CONFIG = {
        TweakState.OPTIMIZED: ("ĐÃ TỐI ƯU", COLOR_SUCCESS, "#064e3b"),
        TweakState.DEFAULT: ("MẶC ĐỊNH", COLOR_WARNING, "#451a03"),
        TweakState.LOADING: ("ĐANG XỬ LÝ...", "#38bdf8", "#082f49"),
        TweakState.ERROR: ("LỖI / ADMIN", COLOR_DANGER, "#450a0a"),
        TweakState.UNSUPPORTED: ("KHÔNG HỖ TRỢ", COLOR_TEXT_DIM, "#1e293b"),
    }

    def __init__(self, master, state: TweakState = TweakState.DEFAULT, **kwargs):
        text, text_col, bg_col = self.STATE_CONFIG.get(state, ("CHỜ", COLOR_TEXT_MUTED, "#1e293b"))
        super().__init__(
            master,
            text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=text_col,
            fg_color=bg_col,
            corner_radius=4,
            padx=8,
            pady=2,
            **kwargs
        )

    def set_state(self, state: TweakState):
        text, text_col, bg_col = self.STATE_CONFIG.get(state, ("CHỜ", COLOR_TEXT_MUTED, "#1e293b"))
        self.configure(text=text, text_color=text_col, fg_color=bg_col)


class HardwareTweakCard(ctk.CTkFrame):
    """Card tinh chỉnh phần cứng CPU/GPU chuẩn Atomic với switch chống nhấn đúp."""

    def __init__(
        self,
        master,
        descriptor: TweakDescriptor,
        initial_state: TweakState,
        on_toggle: Callable[[str, bool, Callable[[bool, str], None]], None],
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
        self.descriptor = descriptor
        self.on_toggle = on_toggle
        self.current_state = initial_state

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        # Left Info Frame
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)

        # Title Row
        title_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        title_row.pack(fill="x", anchor="w")

        title_lbl = ctk.CTkLabel(
            title_row,
            text=self.descriptor.title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        title_lbl.pack(side="left", padx=(0, 8))

        if self.descriptor.requires_reboot:
            reboot_badge = ctk.CTkLabel(
                title_row,
                text="CẦN KHỞI ĐỘNG LẠI",
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                text_color="#f59e0b",
                fg_color="#361a02",
                corner_radius=4,
                padx=6,
                pady=1
            )
            reboot_badge.pack(side="left", padx=4)

        self.badge = StatusBadge(title_row, state=initial_state)
        self.badge.pack(side="left", padx=4)

        # Description
        desc_lbl = ctk.CTkLabel(
            info_frame,
            text=self.descriptor.description,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=640
        )
        desc_lbl.pack(fill="x", anchor="w", pady=(4, 0))

        # Right Action Frame
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="e", padx=16, pady=12)

        self.switch_var = ctk.BooleanVar(value=(initial_state == TweakState.OPTIMIZED))
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
        self.badge.set_state(TweakState.LOADING)

        def on_done(success: bool, msg: str):
            def _update():
                self.switch.configure(state="normal")
                if success:
                    new_st = TweakState.OPTIMIZED if new_val else TweakState.DEFAULT
                    self.current_state = new_st
                    self.badge.set_state(new_st)
                else:
                    self.switch_var.set(not new_val)
                    self.badge.set_state(TweakState.ERROR)
            self.after(0, _update)

        self.on_toggle(self.descriptor.tweak_id, new_val, on_done)

    def update_state(self, state: TweakState):
        self.current_state = state
        self.badge.set_state(state)
        self.switch_var.set(state == TweakState.OPTIMIZED)
        self.switch.configure(state="normal")


class CpuGpuOptimizationTab(ctk.CTkScrollableFrame):
    """Tab Tối Ưu Hóa Phần Cứng Chuyên Sâu (CPU & GPU)."""

    def __init__(
        self,
        master,
        cpu_service: CpuOptimizerService,
        gpu_service: GpuOptimizerService,
        backup_service: RegistryBackupService,
        logger: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.cpu_service = cpu_service
        self.gpu_service = gpu_service
        self.backup_service = backup_service
        self.logger = logger or (lambda msg: None)

        self.cards: Dict[str, HardwareTweakCard] = {}

        self._build_header()
        self._build_toolbar()
        self._build_cpu_section()
        self._build_gpu_section()

    def log(self, msg: str):
        self.logger(msg)

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=4, pady=(0, 10))

        title = ctk.CTkLabel(
            header_frame,
            text="⚡ TỐI ƯU HÓA PHẦN CỨNG CHUYÊN SÂU (CPU & GPU)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        title.pack(anchor="w")

        sub = ctk.CTkLabel(
            header_frame,
            text="Giải phóng toàn diện xung nhịp vi xử lý, mở khóa nhân đồ họa, giảm độ trễ dựng hình và loại bỏ nghẽn cổ chai.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        )
        sub.pack(anchor="w", pady=(2, 0))

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=8,
            height=50
        )
        toolbar.pack(fill="x", padx=4, pady=(0, 14))
        toolbar.pack_propagate(False)

        # Quick Apply All
        self.btn_quick_apply = ctk.CTkButton(
            toolbar,
            text="⚡ Tối Ưu Toàn Bộ (Quick Apply)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            text_color=COLOR_TEXT_WHITE,
            height=32,
            corner_radius=6,
            command=self._handle_quick_apply_all
        )
        self.btn_quick_apply.pack(side="left", padx=(12, 6), pady=8)

        # Revert All
        self.btn_revert = ctk.CTkButton(
            toolbar,
            text="↩️ Khôi Phục Mặc Định (Revert)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            text_color=COLOR_TEXT_WHITE,
            height=32,
            corner_radius=6,
            command=self._handle_revert_all
        )
        self.btn_revert.pack(side="left", padx=6, pady=8)

        # Backup Restore
        self.btn_restore_backup = ctk.CTkButton(
            toolbar,
            text="🛡️ Khôi Phục Từ Bản Sao Lưu",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#1e293b",
            hover_color="#334155",
            text_color=COLOR_TEXT_WHITE,
            height=32,
            corner_radius=6,
            command=self._handle_restore_backup
        )
        self.btn_restore_backup.pack(side="left", padx=6, pady=8)

        # Refresh
        self.btn_refresh = ctk.CTkButton(
            toolbar,
            text="🔄 Làm Mới",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="transparent",
            hover_color="#1e293b",
            text_color=COLOR_TEXT_MUTED,
            width=80,
            height=32,
            corner_radius=6,
            command=self.refresh_all_states
        )
        self.btn_refresh.pack(side="right", padx=(6, 12), pady=8)

    def _build_cpu_section(self):
        # Section Header
        sec_frame = ctk.CTkFrame(self, fg_color="transparent")
        sec_frame.pack(fill="x", padx=4, pady=(6, 8))

        lbl = ctk.CTkLabel(
            sec_frame,
            text="🚀 BỘ TỐI ƯU VI XỬ LÝ (CPU OPTIMIZER) - 5 TINH CHỈNH",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#38bdf8"
        )
        lbl.pack(anchor="w")

        # 5 CPU Tweaks
        cpu_descs = self.cpu_service.get_descriptors()
        for d in cpu_descs:
            st = self.cpu_service.get_status(d.tweak_id)
            card = HardwareTweakCard(
                self,
                descriptor=d,
                initial_state=st,
                on_toggle=self._handle_tweak_toggle
            )
            card.pack(fill="x", padx=4, pady=3)
            self.cards[d.tweak_id] = card

    def _build_gpu_section(self):
        # Section Header
        sec_frame = ctk.CTkFrame(self, fg_color="transparent")
        sec_frame.pack(fill="x", padx=4, pady=(16, 8))

        lbl = ctk.CTkLabel(
            sec_frame,
            text="🎮 BỘ TỐI ƯU ĐỒ HỌA (GPU OPTIMIZER) - 5 TINH CHỈNH",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#a855f7"
        )
        lbl.pack(anchor="w")

        # 5 GPU Tweaks
        gpu_descs = self.gpu_service.get_descriptors()
        for d in gpu_descs:
            st = self.gpu_service.get_status(d.tweak_id)
            card = HardwareTweakCard(
                self,
                descriptor=d,
                initial_state=st,
                on_toggle=self._handle_tweak_toggle
            )
            card.pack(fill="x", padx=4, pady=3)
            self.cards[d.tweak_id] = card

    # -------------------------------------------------------------
    # EVENT HANDLERS
    # -------------------------------------------------------------
    def _handle_tweak_toggle(self, tweak_id: str, enable: bool, callback: Callable[[bool, str], None]):
        def _worker():
            if tweak_id.startswith("cpu_"):
                res = self.cpu_service.apply_tweak(tweak_id) if enable else self.cpu_service.revert_tweak(tweak_id)
            else:
                res = self.gpu_service.apply_tweak(tweak_id) if enable else self.gpu_service.revert_tweak(tweak_id)

            self.log(f"[{'CPU' if tweak_id.startswith('cpu_') else 'GPU'}] {res.message}")
            callback(res.success, res.message)

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_quick_apply_all(self):
        self.btn_quick_apply.configure(state="disabled", text="⏳ Đang Tối Ưu...")
        self.log("[PHẦN CỨNG] Bắt đầu Siêu Tối Ưu CPU & GPU toàn diện...")

        def _worker():
            cpu_res = self.cpu_service.quick_apply_all()
            gpu_res = self.gpu_service.quick_apply_all()

            success_count = sum(1 for r in list(cpu_res.values()) + list(gpu_res.values()) if r.success)
            self.log(f"[PHẦN CỨNG] Hoàn tất tối ưu nhanh: {success_count}/10 thiết lập thành công.")

            def _done():
                self.btn_quick_apply.configure(state="normal", text="⚡ Tối Ưu Toàn Bộ (Quick Apply)")
                self.refresh_all_states()

            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_revert_all(self):
        self.btn_revert.configure(state="disabled", text="⏳ Đang Hoàn Tác...")
        self.log("[PHẦN CỨNG] Đang khôi phục cài đặt CPU & GPU về mặc định...")

        def _worker():
            self.cpu_service.revert_all()
            self.gpu_service.revert_all()
            self.log("[PHẦN CỨNG] Đã khôi phục toàn bộ cài đặt CPU & GPU về mặc định Windows.")

            def _done():
                self.btn_revert.configure(state="normal", text="↩️ Khôi Phục Mặc Định (Revert)")
                self.refresh_all_states()

            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_restore_backup(self):
        self.btn_restore_backup.configure(state="disabled", text="⏳ Đang Phục Hồi...")
        self.log("[SAO LƯU] Đang khôi phục Registry từ bản sao lưu gần nhất...")

        def _worker():
            ok_cpu, msg_cpu = self.backup_service.restore_latest_by_category(TweakCategory.CPU)
            ok_gpu, msg_gpu = self.backup_service.restore_latest_by_category(TweakCategory.GPU)
            self.log(f"[SAO LƯU CPU] {msg_cpu}")
            self.log(f"[SAO LƯU GPU] {msg_gpu}")

            def _done():
                self.btn_restore_backup.configure(state="normal", text="🛡️ Khôi Phục Từ Bản Sao Lưu")
                self.refresh_all_states()

            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def refresh_all_states(self):
        """Kiểm tra và cập nhật lại giao diện thời gian thực của 10 tinh chỉnh."""
        def _worker():
            cpu_status = self.cpu_service.get_all_status()
            gpu_status = self.gpu_service.get_all_status()

            def _update():
                for tid, st in cpu_status.items():
                    if tid in self.cards:
                        self.cards[tid].update_state(st)
                for tid, st in gpu_status.items():
                    if tid in self.cards:
                        self.cards[tid].update_state(st)

            self.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()
