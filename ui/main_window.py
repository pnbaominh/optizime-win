import os
import sys
import threading
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox

from core.engine import OptimizerEngine
from core.tweak_base import Tweak
from core.sys_info import get_windows_version_info, is_admin, get_system_storage_stats
from core.safety import (
    create_system_restore_point,
    list_system_restore_points,
    get_backup_dir
)
from core.cleaner import (
    clean_system_temp_files,
    scan_system_temp_files,
    run_dism_component_cleanup,
    get_installed_bloatware,
    remove_bloatware_package
)
from core.version import APP_NAME, APP_VERSION, GITHUB_REPO_URL
from core.updater import UpdateChecker
from ui.update_dialog import UpdateDialog
from core.startup_manager import list_startup_items, remove_startup_item
from core.network_optimizer import flush_dns_cache, set_primary_dns, reset_dns_to_dhcp, DNS_PROVIDERS
from core.memory_optimizer import trim_memory_working_sets
from ui.theme import (
    COLOR_BG_DARK, COLOR_SIDEBAR_BG, COLOR_CARD_BG, COLOR_BORDER,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER,
    COLOR_WARNING, COLOR_DANGER, COLOR_DANGER_HOVER,
    COLOR_TEXT_WHITE, COLOR_TEXT_MUTED, COLOR_TEXT_DIM, FONT_FAMILY
)
from ui.components import TweakCard, StatBox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Khởi tạo engine
        self.engine = OptimizerEngine()
        self.sys_info = get_windows_version_info()
        self.card_widgets = []

        # Cấu hình cửa sổ
        self.title(f"{APP_NAME} v{APP_VERSION} - Tối Ưu Hóa Windows Chuyên Sâu")
        self.geometry("1060x690")
        self.minsize(940, 600)
        self.configure(fg_color=COLOR_BG_DARK)

        # Cấu hình Icon cho cửa sổ (Window Icon)
        self.base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ico_path = os.path.join(self.base_dir, "assets", "app.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        # Cấu hình Grid Layout
        self.grid_columnconfigure(0, weight=0)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # Main Content
        self.grid_rowconfigure(0, weight=1)

        self._init_sidebar()
        self._init_main_area()
        self.select_tab("dashboard")
        self.log(f"Ứng dụng {APP_NAME} v{APP_VERSION} đã khởi động trên {self.sys_info['full_name']}")
        if not self.sys_info["is_admin"]:
            self.log("[CẢNH BÁO] Ứng dụng chưa chạy quyền Administrator. Một số tính năng Registry/Service cần quyền Quản trị.")

        # Tự động kiểm tra bản cập nhật mới trong background (không ảnh hưởng tốc độ mở app)
        threading.Thread(target=self._check_for_updates_silently, daemon=True).start()

    # -------------------------------------------------------------
    # SIDEBAR
    # -------------------------------------------------------------
    def _init_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self,
            width=230,
            corner_radius=0,
            fg_color=COLOR_SIDEBAR_BG,
            border_color=COLOR_BORDER,
            border_width=1
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)

        # App Logo & Title
        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=14, pady=(16, 12))

        # Hiển thị Logo App hiện đại
        png_path = os.path.join(self.base_dir, "assets", "logo.png")
        if os.path.exists(png_path):
            try:
                from PIL import Image
                pil_img = Image.open(png_path)
                self.logo_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(40, 40))
                logo_display = ctk.CTkLabel(title_frame, image=self.logo_ctk, text="")
                logo_display.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        title_texts = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_texts.pack(side="left", fill="y", expand=True)

        logo_lbl = ctk.CTkLabel(
            title_texts,
            text="DEEP OPTIMIZER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        logo_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            title_texts,
            text="Windows 10 / 11 Tuner",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_DIM
        )
        sub_lbl.pack(anchor="w")

        # System Info Card
        sys_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=6
        )
        sys_card.pack(fill="x", padx=14, pady=(0, 14))

        os_lbl = ctk.CTkLabel(
            sys_card,
            text=f"💻 {self.sys_info['os_name']} {self.sys_info['version_tag']}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        os_lbl.pack(anchor="w", padx=10, pady=(8, 2))

        admin_text = "🛡️ Quyền: Administrator" if self.sys_info["is_admin"] else "⚠️ Quyền: Standard User"
        admin_color = COLOR_SUCCESS if self.sys_info["is_admin"] else COLOR_WARNING
        admin_lbl = ctk.CTkLabel(
            sys_card,
            text=admin_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=admin_color
        )
        admin_lbl.pack(anchor="w", padx=10, pady=(0, 4))

        if not self.sys_info["is_admin"]:
            admin_btn = ctk.CTkButton(
                sys_card,
                text="🛡️ Chạy lại quyền Admin",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                fg_color="#dc2626",
                hover_color="#b91c1c",
                height=24,
                corner_radius=4,
                command=self._restart_as_admin
            )
            admin_btn.pack(anchor="w", padx=10, pady=(0, 8))

        # Footer Sidebar (Version & Auto Update) - pack first so it sticks to bottom
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=12, pady=12)

        ver_lbl = ctk.CTkLabel(
            footer,
            text=f"Phiên bản: v{APP_VERSION}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_DIM
        )
        ver_lbl.pack(anchor="w", pady=(0, 4))

        update_btn = ctk.CTkButton(
            footer,
            text="🔄 Kiểm tra cập nhật",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            text_color=COLOR_TEXT_WHITE,
            height=30,
            corner_radius=6,
            command=self._check_for_updates_manually
        )
        update_btn.pack(fill="x")

        # Navigation Scrollable Area (between sys_card and footer)
        nav_container = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        nav_container.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.nav_buttons = {}
        tabs = [
            ("dashboard", "🏠  Bảng Điều Khiển"),
            ("safety", "🛡️  An Toàn & Khôi Phục"),
            ("privacy", "🔒  Quyền Riêng Tư"),
            ("services", "⚙️  Dịch Vụ Hệ Thống"),
            ("performance", "🚀  Hiệu Năng & Game"),
            ("startup", "⚡  Quản Lý Khởi Động"),
            ("network", "🌐  Mạng & DNS"),
            ("cleaner", "🧹  Dọn Rác & Bloatware"),
            ("logs", "📜  Nhật Ký Hoạt Động")
        ]

        for tab_id, tab_label in tabs:
            btn = ctk.CTkButton(
                nav_container,
                text=tab_label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                fg_color="transparent",
                text_color=COLOR_TEXT_MUTED,
                hover_color="#1e293b",
                anchor="w",
                height=36,
                corner_radius=6,
                command=lambda tid=tab_id: self.select_tab(tid)
            )
            btn.pack(fill="x", padx=6, pady=2)
            self.nav_buttons[tab_id] = btn

    # -------------------------------------------------------------
    # MAIN AREA & TOP ACTION BAR
    # -------------------------------------------------------------
    def _init_main_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=16)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Top Action Bar
        top_bar = ctk.CTkFrame(
            self.main_container,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=8,
            height=56
        )
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        top_bar.pack_propagate(False)

        top_lbl = ctk.CTkLabel(
            top_bar,
            text="HỆ THỐNG AN TOÀN & TỐI ƯU HÓA CHUYÊN SÂU",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        top_lbl.pack(side="left", padx=16)

        # Top Buttons
        btn_rollback = ctk.CTkButton(
            top_bar,
            text="🔄 Hoàn Tác Tất Cả",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            text_color=COLOR_TEXT_WHITE,
            width=130,
            height=32,
            corner_radius=6,
            command=self._handle_revert_all
        )
        btn_rollback.pack(side="right", padx=(6, 14))

        btn_optimize_all = ctk.CTkButton(
            top_bar,
            text="⚡ Tối Ưu Nhanh (Khuyên Dùng)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color=COLOR_TEXT_WHITE,
            width=190,
            height=32,
            corner_radius=6,
            command=self._handle_optimize_all
        )
        btn_optimize_all.pack(side="right", padx=6)

        btn_create_rp = ctk.CTkButton(
            top_bar,
            text="🛡️ Tạo Restore Point",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#065f46",
            hover_color="#047857",
            text_color=COLOR_TEXT_WHITE,
            width=150,
            height=32,
            corner_radius=6,
            command=self._handle_quick_restore_point
        )
        btn_create_rp.pack(side="right", padx=6)

        # Content Views Dictionary
        self.views = {}
        self.views["dashboard"] = self._create_dashboard_view()
        self.views["safety"] = self._create_safety_view()
        self.views["privacy"] = self._create_category_view("Quyền Riêng Tư")
        self.views["services"] = self._create_category_view("Dịch Vụ Hệ Thống")
        self.views["performance"] = self._create_category_view("Hiệu Năng & Gaming")
        self.views["startup"] = self._create_startup_view()
        self.views["network"] = self._create_network_view()
        self.views["cleaner"] = self._create_cleaner_view()
        self.views["logs"] = self._create_logs_view()

    # -------------------------------------------------------------
    # TAB SWITCHING
    # -------------------------------------------------------------
    def select_tab(self, tab_id: str):
        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(fg_color="#1e293b", text_color=COLOR_PRIMARY)
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_MUTED)

        for tid, view in self.views.items():
            if tid == tab_id:
                view.grid(row=1, column=0, sticky="nsew")
            else:
                view.grid_forget()

        if tab_id == "dashboard":
            self._update_dashboard_kpis()

    # -------------------------------------------------------------
    # VIEW: DASHBOARD
    # -------------------------------------------------------------
    def _create_dashboard_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        # KPI Cards Row
        kpi_frame = ctk.CTkFrame(frame, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 16))
        kpi_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.kpi_total = StatBox(kpi_frame, "TỔNG SỐ TINH CHỈNH", "15", "100% An toàn & Thực chất", height=95)
        self.kpi_total.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.kpi_applied = StatBox(kpi_frame, "ĐÃ ĐƯỢC TỐI ƯU", "0", "0 / 15 mục", badge_color=COLOR_SUCCESS, height=95)
        self.kpi_applied.grid(row=0, column=1, sticky="ew", padx=4)

        storage = get_system_storage_stats()
        self.kpi_storage = StatBox(
            kpi_frame,
            "Ổ ĐĨA C: HỆ THỐNG",
            f"{storage['free_gb']} GB",
            f"Trống {storage['free_percent']}% trên {storage['total_gb']} GB",
            badge_color="#38bdf8",
            height=95
        )
        self.kpi_storage.grid(row=0, column=2, sticky="ew", padx=(8, 0))

        # Banner Khuyến nghị & Giới thiệu
        banner = ctk.CTkFrame(
            frame,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=8
        )
        banner.pack(fill="x", pady=(0, 16))

        b_title = ctk.CTkLabel(
            banner,
            text="✨ Chào mừng bạn đến với Windows Deep Optimizer",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        b_title.pack(anchor="w", padx=16, pady=(14, 4))

        b_desc = ctk.CTkLabel(
            banner,
            text=(
                "Ứng dụng được thiết kế theo chuẩn an toàn hàng đầu dành cho Windows 10 và Windows 11:\n"
                "• Không gây lỗi hệ điều hành (Zero-Brick): Tự động tạo điểm khôi phục System Restore trước khi can thiệp.\n"
                "• Không sử dụng chiêu trò 'giả dược' (No Snake-oil): Không dọn RAM ảo, không vô hiệu hóa Windows Update hay Defender.\n"
                "• Khôi phục 100%: Mọi tinh chỉnh đều có thể hoàn tác về nguyên bản chỉ với 1 cú click chuột."
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT_MUTED,
            justify="left"
        )
        b_desc.pack(anchor="w", padx=16, pady=(0, 14))

        # Quick Actions Grid
        actions_frame = ctk.CTkFrame(frame, fg_color="transparent")
        actions_frame.pack(fill="both", expand=True)
        actions_frame.grid_columnconfigure((0, 1), weight=1)

        # Box 1: Tối ưu 1-click
        act_box1 = ctk.CTkFrame(actions_frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        act_box1.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=4)

        a1_title = ctk.CTkLabel(act_box1, text="⚡ Tối Ưu Tức Thời (Khuyên Dùng)", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_WHITE)
        a1_title.pack(anchor="w", padx=16, pady=(14, 4))

        a1_desc = ctk.CTkLabel(
            act_box1,
            text="Áp dụng tất cả các tinh chỉnh an toàn được khuyến nghị (Tắt Telemetry ngầm, giảm Menu Delay, tối ưu TCP Stack, tắt Xbox DVR background).",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=340,
            justify="left"
        )
        a1_desc.pack(anchor="w", padx=16, pady=(0, 12))

        a1_btn = ctk.CTkButton(
            act_box1,
            text="Bắt Đầu Tối Ưu An Toàn",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._handle_optimize_all,
            height=34,
            corner_radius=6
        )
        a1_btn.pack(anchor="w", padx=16, pady=(0, 14))

        # Box 2: Dọn dẹp ổ đĩa
        act_box2 = ctk.CTkFrame(actions_frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        act_box2.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=4)

        a2_title = ctk.CTkLabel(act_box2, text="🧹 Dọn Rác & Bộ Nhớ Đệm", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_WHITE)
        a2_title.pack(anchor="w", padx=16, pady=(14, 4))

        a2_desc = ctk.CTkLabel(
            act_box2,
            text="Xóa sạch các tệp tin tạm của người dùng (%TEMP%) và Windows Temp mà không ảnh hưởng đến các ứng dụng đang hoạt động.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=340,
            justify="left"
        )
        a2_desc.pack(anchor="w", padx=16, pady=(0, 12))

        a2_btn = ctk.CTkButton(
            act_box2,
            text="Dọn Dẹp File Tạm Ngay",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color="#0891b2",
            hover_color="#0e7490",
            command=self._handle_clean_temp,
            height=34,
            corner_radius=6
        )
        a2_btn.pack(anchor="w", padx=16, pady=(0, 14))

        return frame

    def _update_dashboard_kpis(self):
        tweaks = self.engine.get_all_tweaks()
        total = len(tweaks)
        applied = sum(1 for t in tweaks if t.check())
        self.kpi_total.update_value(str(total), "100% An toàn & Thực chất")
        self.kpi_applied.update_value(str(applied), f"{applied} / {total} mục đã tối ưu")

        storage = get_system_storage_stats()
        self.kpi_storage.update_value(
            f"{storage['free_gb']} GB",
            f"Trống {storage['free_percent']}% trên {storage['total_gb']} GB"
        )

    # -------------------------------------------------------------
    # VIEW: SAFETY & RESTORE POINT
    # -------------------------------------------------------------
    def _create_safety_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")

        # Section: Tạo Restore Point mới
        create_box = ctk.CTkFrame(frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        create_box.pack(fill="x", pady=(0, 14))

        lbl = ctk.CTkLabel(
            create_box,
            text="🛡️ Tạo Điểm Khôi Phục Hệ Thống (System Restore Point)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        lbl.pack(anchor="w", padx=16, pady=(14, 4))

        sub = ctk.CTkLabel(
            create_box,
            text="Tạo một điểm mốc hoàn chỉnh của Windows. Nếu xảy ra bất kỳ sự cố ngoài ý muốn nào, bạn có thể quay trở lại thời điểm này ngay tức thì.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        )
        sub.pack(anchor="w", padx=16, pady=(0, 12))

        input_row = ctk.CTkFrame(create_box, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=(0, 14))

        self.rp_name_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Nhập ghi chú cho điểm khôi phục (Ví dụ: Truoc_Khi_Choi_Game)...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            height=36,
            fg_color="#0f172a",
            border_color=COLOR_BORDER
        )
        self.rp_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        rp_btn = ctk.CTkButton(
            input_row,
            text="Tạo Điểm Khôi Phục",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            height=36,
            command=self._handle_manual_restore_point
        )
        rp_btn.pack(side="right")

        # Section: Danh sách Restore Points hiện có
        list_box = ctk.CTkFrame(frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        list_box.pack(fill="both", expand=True, pady=(0, 14))

        top_list_row = ctk.CTkFrame(list_box, fg_color="transparent")
        top_list_row.pack(fill="x", padx=16, pady=(12, 8))

        lbl_list = ctk.CTkLabel(
            top_list_row,
            text="📋 Danh Sách Điểm Khôi Phục Hiện Có",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        lbl_list.pack(side="left")

        refresh_btn = ctk.CTkButton(
            top_list_row,
            text="🔄 Làm mới",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=80,
            height=28,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self._refresh_restore_points
        )
        refresh_btn.pack(side="right", padx=6)

        open_backup_btn = ctk.CTkButton(
            top_list_row,
            text="📁 Mở Thư Mục Backup Registry",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=180,
            height=28,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self._open_backup_folder
        )
        open_backup_btn.pack(side="right")

        self.rp_scroll = ctk.CTkScrollableFrame(list_box, fg_color="#090d16", corner_radius=6)
        self.rp_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        self._refresh_restore_points()
        return frame

    def _refresh_restore_points(self):
        for w in self.rp_scroll.winfo_children():
            w.destroy()

        def fetch():
            rps = list_system_restore_points()
            self.after(0, lambda: self._render_restore_points(rps))

        threading.Thread(target=fetch, daemon=True).start()

    def _render_restore_points(self, rps: list):
        if not rps:
            empty_lbl = ctk.CTkLabel(
                self.rp_scroll,
                text="Chưa có điểm khôi phục nào được tạo gần đây (Hoặc System Protection đang tắt).",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLOR_TEXT_DIM
            )
            empty_lbl.pack(pady=20)
            return

        for rp in rps:
            item = ctk.CTkFrame(self.rp_scroll, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=6)
            item.pack(fill="x", pady=4, padx=4)

            desc = rp.get("Description", "Restore Point")
            seq = rp.get("SequenceNumber", "#")
            time_str = rp.get("CreationTime", "")

            title = ctk.CTkLabel(
                item,
                text=f"#{seq}: {desc}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=COLOR_TEXT_WHITE
            )
            title.pack(anchor="w", padx=12, pady=(8, 2))

            time_lbl = ctk.CTkLabel(
                item,
                text=f"Thời gian tạo: {time_str}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_TEXT_MUTED
            )
            time_lbl.pack(anchor="w", padx=12, pady=(0, 8))

    def _restart_as_admin(self):
        from core.sys_info import elevate_if_not_admin
        if elevate_if_not_admin():
            self.destroy()
            sys.exit(0)
        else:
            messagebox.showinfo("Thông Báo", "Yêu cầu cấp quyền Administrator đã bị hủy hoặc từ chối.")

    # -------------------------------------------------------------
    # VIEW: CATEGORIES (PRIVACY, SERVICES, PERFORMANCE)
    # -------------------------------------------------------------
    def _create_category_view(self, category_name: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        if category_name == "Dịch Vụ Hệ Thống" and not self.sys_info["is_admin"]:
            admin_banner = ctk.CTkFrame(scroll, fg_color="#3b0764", border_color="#7c3aed", border_width=1, corner_radius=8)
            admin_banner.pack(fill="x", pady=(0, 12))

            b_info = ctk.CTkFrame(admin_banner, fg_color="transparent")
            b_info.pack(side="left", padx=14, pady=10, fill="x", expand=True)

            w_title = ctk.CTkLabel(
                b_info,
                text="⚠️ YÊU CẦU QUYỀN QUẢN TRỊ VIÊN (ADMINISTRATOR)",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color="#fde047"
            )
            w_title.pack(anchor="w")

            w_desc = ctk.CTkLabel(
                b_info,
                text="Bạn đang chạy ứng dụng với quyền Standard User. Quản lý dịch vụ Windows bắt buộc quyền Administrator để lưu cấu hình.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT_WHITE
            )
            w_desc.pack(anchor="w", pady=(2, 0))

            admin_btn = ctk.CTkButton(
                admin_banner,
                text="🛡️ Khởi động lại quyền Admin",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                fg_color="#dc2626",
                hover_color="#b91c1c",
                height=32,
                command=self._restart_as_admin
            )
            admin_btn.pack(side="right", padx=14, pady=10)

        tweaks = self.engine.get_tweaks_by_category(category_name)
        for tweak in tweaks:
            card = TweakCard(
                scroll,
                tweak=tweak,
                on_toggle=self._handle_tweak_toggle,
                on_show_info=self._show_tweak_info
            )
            card.pack(fill="x", pady=6)
            self.card_widgets.append(card)

        return frame

    def _handle_tweak_toggle(self, tweak: Tweak, new_value: bool):
        def worker():
            if new_value:
                self.log(f"Đang áp dụng: {tweak.name}...")
                ok, msg = tweak.apply()
            else:
                self.log(f"Đang hoàn tác: {tweak.name}...")
                ok, msg = tweak.revert()

            status_icon = "[+]" if ok else "[!]"
            self.log(f"{status_icon} {tweak.name}: {msg}")
            self.after(0, self._refresh_all_cards)

            if not ok:
                action_str = "áp dụng" if new_value else "hoàn tác"
                self.after(0, lambda: messagebox.showwarning(
                    "Thông Báo Quyền Hệ Thống",
                    f"Không thể {action_str} tùy chọn '{tweak.name}':\n\n{msg}\n\n"
                    "Lưu ý: Bạn cần chạy ứng dụng với quyền Quản Trị Viên (Run as Administrator) để cấu hình Dịch vụ hệ thống."
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_all_cards(self):
        for card in self.card_widgets:
            card.refresh_state()
        self._update_dashboard_kpis()

    def _show_tweak_info(self, tweak: Tweak):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Chi Tiết: {tweak.name}")
        dialog.geometry("540x380")
        dialog.configure(fg_color=COLOR_BG_DARK)
        dialog.transient(self)
        dialog.grab_set()

        lbl_title = ctk.CTkLabel(
            dialog,
            text=tweak.name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        lbl_title.pack(anchor="w", padx=20, pady=(20, 6))

        badge = ctk.CTkLabel(
            dialog,
            text=f"Danh mục: {tweak.category}  |  Khuyên dùng: {'Có' if tweak.is_recommended else 'Nâng cao'}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_PRIMARY
        )
        badge.pack(anchor="w", padx=20, pady=(0, 14))

        box = ctk.CTkTextbox(
            dialog,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_BORDER,
            border_width=1,
            text_color=COLOR_TEXT_WHITE,
            wrap="word"
        )
        box.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        box.insert("1.0", tweak.explanation)
        box.configure(state="disabled")

        btn_close = ctk.CTkButton(
            dialog,
            text="Đã Hiểu & Đóng",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=dialog.destroy,
            height=36
        )
        btn_close.pack(fill="x", padx=20, pady=(0, 20))

    # -------------------------------------------------------------
    # VIEW: CLEANER & BLOATWARE
    # -------------------------------------------------------------
    def _create_cleaner_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Card 1: Dọn dẹp File Tạm
        c1 = ctk.CTkFrame(scroll, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        c1.pack(fill="x", pady=6)

        c1_title = ctk.CTkLabel(c1, text="🧹 Dọn Dẹp File Tạm (%TEMP% & Windows Temp)", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=COLOR_TEXT_WHITE)
        c1_title.pack(anchor="w", padx=16, pady=(14, 4))

        c1_desc = ctk.CTkLabel(
            c1,
            text="Xóa các tệp rác sinh ra từ trình duyệt, bộ cài đặt cũ và tiến trình Windows. Bỏ qua an toàn các tệp đang mở.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        )
        c1_desc.pack(anchor="w", padx=16, pady=(0, 10))

        self.c1_status_lbl = ctk.CTkLabel(
            c1,
            text="Trạng thái: Sẵn sàng dọn dẹp bộ nhớ đệm.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#38bdf8"
        )
        self.c1_status_lbl.pack(anchor="w", padx=16, pady=(0, 10))

        btn_row1 = ctk.CTkFrame(c1, fg_color="transparent")
        btn_row1.pack(anchor="w", padx=16, pady=(0, 14))

        self.c1_btn = ctk.CTkButton(
            btn_row1,
            text="🧹 Dọn Dẹp File Tạm Ngay",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._handle_clean_temp,
            height=34
        )
        self.c1_btn.pack(side="left", padx=(0, 8))

        self.c1_scan_btn = ctk.CTkButton(
            btn_row1,
            text="🔍 Quét Thử Dung Lượng Rác",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#1e293b",
            hover_color="#334155",
            command=self._handle_scan_temp,
            height=34
        )
        self.c1_scan_btn.pack(side="left")

        # Card 2: DISM Component Cleanup
        c2 = ctk.CTkFrame(scroll, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        c2.pack(fill="x", pady=6)

        c2_title = ctk.CTkLabel(c2, text="🗜️ Dọn Dẹp Windows Component Store (WinSxS)", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=COLOR_TEXT_WHITE)
        c2_title.pack(anchor="w", padx=16, pady=(14, 4))

        c2_desc = ctk.CTkLabel(
            c2,
            text="Chạy lệnh chuẩn của Microsoft (DISM StartComponentCleanup) để xóa các phiên bản cũ của Windows Update, giải phóng hàng chục GB.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        )
        c2_desc.pack(anchor="w", padx=16, pady=(0, 10))

        self.c2_status_lbl = ctk.CTkLabel(
            c2,
            text="Trạng thái: Sẵn sàng thực thi. Tiến trình này chạy nền an toàn.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_DIM
        )
        self.c2_status_lbl.pack(anchor="w", padx=16, pady=(0, 10))

        self.c2_btn = ctk.CTkButton(
            c2,
            text="🗜️ Chạy Dọn Dẹp DISM",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color="#0891b2",
            hover_color="#0e7490",
            command=self._handle_dism_cleanup,
            height=34
        )
        self.c2_btn.pack(anchor="w", padx=16, pady=(0, 14))

        # Card 3: Gỡ Bloatware an toàn
        c3 = ctk.CTkFrame(scroll, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        c3.pack(fill="x", pady=6)

        c3_title_row = ctk.CTkFrame(c3, fg_color="transparent")
        c3_title_row.pack(fill="x", padx=16, pady=(14, 4))

        c3_title = ctk.CTkLabel(c3_title_row, text="🗑️ Gỡ Bỏ Ứng Dụng Rác Cài Sẵn (Safe Bloatware Remover)", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=COLOR_TEXT_WHITE)
        c3_title.pack(side="left")

        c3_refresh_btn = ctk.CTkButton(
            c3_title_row,
            text="🔄 Quét lại",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=80,
            height=26,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self._refresh_bloatware_ui
        )
        c3_refresh_btn.pack(side="right")

        c3_desc = ctk.CTkLabel(
            c3,
            text="Hệ thống quét các ứng dụng quảng cáo, game rác hoặc app tài trợ cài ngầm trong Windows. Bạn có thể chọn để gỡ bỏ triệt để.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        )
        c3_desc.pack(anchor="w", padx=16, pady=(0, 10))

        self.bloat_container = ctk.CTkFrame(c3, fg_color="transparent")
        self.bloat_container.pack(fill="x", padx=16, pady=(0, 14))

        self.c3_btn = ctk.CTkButton(
            c3,
            text="🗑️ Gỡ Các Ứng Dụng Đã Chọn",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            command=self._handle_remove_bloatware,
            height=34
        )

        self._refresh_bloatware_ui()
        return frame

    def _refresh_bloatware_ui(self):
        for w in self.bloat_container.winfo_children():
            w.destroy()

        self.bloatware_checks = {}
        bloat_list = get_installed_bloatware()
        installed = [app for app in bloat_list if app["is_installed"]]

        if not installed:
            clean_card = ctk.CTkFrame(self.bloat_container, fg_color="#064e3b", border_color="#059669", border_width=1, corner_radius=6)
            clean_card.pack(fill="x", pady=4)

            lbl_clean = ctk.CTkLabel(
                clean_card,
                text="🎉 Tuyệt vời! Hiện không phát hiện ứng dụng rác nào được cài đặt trên máy tính của bạn.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color="#6ee7b7"
            )
            lbl_clean.pack(anchor="w", padx=14, pady=(10, 2))

            lbl_sub = ctk.CTkLabel(
                clean_card,
                text="Tất cả 13 ứng dụng rác/quảng cáo phổ biến (TikTok, Disney+, Solitaire, Feedback Hub, v.v.) đều sạch sẽ.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color="#a7f3d0"
            )
            lbl_sub.pack(anchor="w", padx=14, pady=(0, 10))

            if hasattr(self, 'c3_btn'):
                self.c3_btn.pack_forget()
            return

        header_frame = ctk.CTkFrame(self.bloat_container, fg_color="#090d16", corner_radius=6)
        header_frame.pack(fill="x", pady=(0, 6))

        select_all_var = ctk.BooleanVar(value=False)
        def toggle_all():
            val = select_all_var.get()
            for v, _ in self.bloatware_checks.values():
                v.set(val)

        cb_all = ctk.CTkCheckBox(
            header_frame,
            text=f"Chọn tất cả ({len(installed)} ứng dụng được tìm thấy)",
            variable=select_all_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
            command=toggle_all
        )
        cb_all.pack(anchor="w", padx=12, pady=8)

        items_frame = ctk.CTkFrame(self.bloat_container, fg_color="#090d16", corner_radius=6)
        items_frame.pack(fill="x")

        for app in installed:
            var = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(
                items_frame,
                text=f"{app['name']} — {app['desc']}",
                variable=var,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=COLOR_TEXT_WHITE,
                state="normal"
            )
            cb.pack(anchor="w", padx=12, pady=6)
            self.bloatware_checks[app["id"]] = (var, app["name"])

        if hasattr(self, 'c3_btn'):
            self.c3_btn.pack(anchor="w", padx=16, pady=(0, 14))
            self.c3_btn.configure(state="normal", text="🗑️ Gỡ Các Ứng Dụng Đã Chọn")

    def _handle_scan_temp(self):
        self.c1_scan_btn.configure(state="disabled", text="⏳ Đang quét...")
        def worker():
            res = scan_system_temp_files()
            self.after(0, lambda: self.c1_status_lbl.configure(text=f"📊 {res['message']}"))
            self.after(0, lambda: self.c1_scan_btn.configure(state="normal", text="🔍 Quét Thử Dung Lượng Rác"))
        threading.Thread(target=worker, daemon=True).start()

    def _handle_clean_temp(self):
        self.c1_btn.configure(state="disabled", text="⏳ Đang dọn dẹp file tạm...")
        self.c1_status_lbl.configure(text="⏳ Đang quét và xóa các file rác trong %TEMP% và Windows Temp...")
        def worker():
            self.log("Đang bắt đầu dọn dẹp file tạm hệ thống...")
            res = clean_system_temp_files()
            self.log(f"[+] {res['message']}")
            self.after(0, lambda: self.c1_btn.configure(state="normal", text="🧹 Dọn Dẹp File Tạm Ngay"))
            self.after(0, lambda: self.c1_status_lbl.configure(text=f"✅ {res['message']}"))
            self.after(0, lambda: messagebox.showinfo("Dọn Dẹp Xong", res['message']))
            self.after(0, self._update_dashboard_kpis)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_dism_cleanup(self):
        if not messagebox.askyesno("Xác Nhận", "Tiến trình dọn dẹp DISM có thể mất từ 2 đến 5 phút tùy tốc độ máy.\nBạn có muốn bắt đầu không?"):
            return

        self.c2_btn.configure(state="disabled", text="⏳ Đang chạy DISM Component Cleanup...")
        self.c2_status_lbl.configure(text="⏳ DISM đang thu gọn thư mục WinSxS trong nền. Vui lòng không tắt máy...")
        def worker():
            self.log("Đang chạy lệnh DISM Component Store Cleanup (Vui lòng chờ)...")
            ok, msg = run_dism_component_cleanup()
            status = "[+]" if ok else "[!]"
            self.log(f"{status} {msg}")
            self.after(0, lambda: self.c2_btn.configure(state="normal", text="🗜️ Chạy Dọn Dẹp DISM"))
            self.after(0, lambda: self.c2_status_lbl.configure(text=f"✅ {msg}" if ok else f"⚠️ {msg}"))
            self.after(0, lambda: messagebox.showinfo("Kết Quả DISM", msg))
            self.after(0, self._update_dashboard_kpis)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_remove_bloatware(self):
        to_remove = [app_id for app_id, (var, name) in self.bloatware_checks.items() if var.get()]
        if not to_remove:
            messagebox.showinfo("Thông Báo", "Vui lòng tích chọn ít nhất 1 ứng dụng để gỡ bỏ.")
            return

        if not messagebox.askyesno("Xác Nhận Gỡ Bỏ", f"Bạn có chắc muốn gỡ {len(to_remove)} ứng dụng đã chọn không?"):
            return

        self.c3_btn.configure(state="disabled", text="⏳ Đang gỡ bỏ...")
        def worker():
            self.log(f"Bắt đầu gỡ bỏ {len(to_remove)} ứng dụng rác...")
            for app_id in to_remove:
                _, name = self.bloatware_checks[app_id]
                self.log(f"Đang gỡ {name}...")
                ok, msg = remove_bloatware_package(app_id)
                status = "[+]" if ok else "[!]"
                self.log(f"{status} {msg}")
            self.log("--- GỠ BLOATWARE HOÀN TẤT ---")
            self.after(0, lambda: messagebox.showinfo("Hoàn Tất", "Đã gỡ các ứng dụng bloatware được chọn."))
            self.after(0, self._refresh_bloatware_ui)

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------
    # VIEW: LOGS
    # -------------------------------------------------------------
    def _create_logs_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")

        top_row = ctk.CTkFrame(frame, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 10))

        lbl = ctk.CTkLabel(top_row, text="📜 Nhật Ký Thực Thi Hệ Thống (Live Console)", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_WHITE)
        lbl.pack(side="left")

        clear_btn = ctk.CTkButton(top_row, text="Xóa Nhật Ký", font=ctk.CTkFont(family=FONT_FAMILY, size=11), width=90, height=28, fg_color="#1e293b", hover_color="#334155", command=self._clear_logs)
        clear_btn.pack(side="right")

        self.log_box = ctk.CTkTextbox(
            frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#090d16",
            border_color=COLOR_BORDER,
            border_width=1,
            text_color="#e2e8f0"
        )
        self.log_box.pack(fill="both", expand=True)

        return frame

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"
        if hasattr(self, 'log_box'):
            self.log_box.insert("end", formatted)
            self.log_box.see("end")
        print(formatted, end="")

    def _clear_logs(self):
        if hasattr(self, 'log_box'):
            self.log_box.delete("1.0", "end")

    # -------------------------------------------------------------
    # TOP BAR ACTIONS
    # -------------------------------------------------------------
    def _handle_quick_restore_point(self):
        def worker():
            self.log("Đang tạo Restore Point nhanh...")
            ok, msg = create_system_restore_point("QuickBackup")
            self.log(f"-> {msg}")
            self.after(0, lambda: messagebox.showinfo("Restore Point", msg))
            self.after(0, self._refresh_restore_points)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_manual_restore_point(self):
        custom_name = self.rp_name_entry.get().strip() or "ManualBackup"

        def worker():
            self.log(f"Đang tạo điểm khôi phục: {custom_name}...")
            ok, msg = create_system_restore_point(custom_name)
            self.log(f"-> {msg}")
            self.after(0, lambda: messagebox.showinfo("Restore Point", msg))
            self.after(0, self._refresh_restore_points)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_optimize_all(self):
        if not messagebox.askyesno(
            "Xác Nhận Tối Ưu An Toàn",
            "Ứng dụng sẽ tự động tạo Điểm Khôi Phục Hệ Thống trước khi áp dụng các tinh chỉnh an toàn.\n\n"
            "Bạn có muốn tiếp tục không?"
        ):
            return

        def worker():
            self.engine.apply_all_recommended(log_callback=self.log)
            self.after(0, self._refresh_all_cards)
            self.after(0, lambda: messagebox.showinfo("Hoàn Tất", "Đã hoàn thành tối ưu hóa hệ thống an toàn!"))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_revert_all(self):
        if not messagebox.askyesno(
            "Xác Nhận Hoàn Tác",
            "Tất cả các tinh chỉnh đang được áp dụng sẽ được đưa về giá trị mặc định của Windows.\n\n"
            "Bạn có muốn hoàn tác không?"
        ):
            return

        def worker():
            self.engine.revert_all(log_callback=self.log)
            self.after(0, self._refresh_all_cards)
            self.after(0, lambda: messagebox.showinfo("Hoàn Tất", "Đã khôi phục toàn bộ thiết lập về mặc định của Windows!"))

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------
    # AUTO-UPDATE METHODS
    # -------------------------------------------------------------
    def _check_for_updates_silently(self):
        try:
            update_info = UpdateChecker.check_for_updates()
            if update_info and update_info.get("has_update"):
                self.after(1500, lambda: UpdateDialog(self, update_info))
        except Exception:
            pass

    def _check_for_updates_manually(self):
        self.log("Đang kiểm tra bản cập nhật mới từ GitHub...")
        def worker():
            update_info = UpdateChecker.check_for_updates()
            if update_info and update_info.get("has_update"):
                self.after(0, lambda: UpdateDialog(self, update_info))
            else:
                self.after(0, lambda: messagebox.showinfo(
                    "Kiểm Tra Cập Nhật",
                    f"Bạn đang sử dụng phiên bản mới nhất (v{APP_VERSION})!\nKhông có bản cập nhật mới nào."
                ))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------
    # VIEW: STARTUP MANAGER
    # -------------------------------------------------------------
    def _create_startup_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")

        top_box = ctk.CTkFrame(frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        top_box.pack(fill="x", pady=(0, 14))

        lbl = ctk.CTkLabel(
            top_box,
            text="⚡ Quản Lý Ứng Dụng Tự Khởi Động Cùng Windows",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        lbl.pack(anchor="w", padx=16, pady=(14, 4))

        sub = ctk.CTkLabel(
            top_box,
            text="Tắt các phần mềm không cần thiết tự chạy khi mở máy giúp tăng tốc thời gian khởi động Windows và giải phóng RAM.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        )
        sub.pack(anchor="w", padx=16, pady=(0, 14))

        # Danh sách Startup Items
        list_box = ctk.CTkFrame(frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        list_box.pack(fill="both", expand=True)

        header_row = ctk.CTkFrame(list_box, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(
            header_row,
            text="Danh Sách Ứng Dụng Khởi Động Đang Hoạt Động",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        ).pack(side="left")

        refresh_btn = ctk.CTkButton(
            header_row,
            text="🔄 Làm mới",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=90,
            height=28,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self._refresh_startup_items
        )
        refresh_btn.pack(side="right")

        self.startup_scroll = ctk.CTkScrollableFrame(list_box, fg_color="#090d16", corner_radius=6)
        self.startup_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        self._refresh_startup_items()
        return frame

    def _refresh_startup_items(self):
        for w in self.startup_scroll.winfo_children():
            w.destroy()

        items = list_startup_items()
        if not items:
            ctk.CTkLabel(
                self.startup_scroll,
                text="Không có ứng dụng khởi động nào được đăng ký trong Registry.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLOR_TEXT_DIM
            ).pack(pady=40)
            return

        for it in items:
            row = ctk.CTkFrame(self.startup_scroll, fg_color="#131d2e", corner_radius=6)
            row.pack(fill="x", pady=4, padx=4)

            info_f = ctk.CTkFrame(row, fg_color="transparent")
            info_f.pack(side="left", fill="both", expand=True, padx=12, pady=8)

            title_row = ctk.CTkFrame(info_f, fg_color="transparent")
            title_row.pack(fill="x")

            ctk.CTkLabel(
                title_row,
                text=it["name"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=COLOR_TEXT_WHITE
            ).pack(side="left")

            badge = ctk.CTkLabel(
                title_row,
                text=it["location"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color="#94a3b8",
                fg_color="#1e293b",
                corner_radius=4,
                padx=6,
                pady=2
            )
            badge.pack(side="left", padx=8)

            ctk.CTkLabel(
                info_f,
                text=it["command"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_TEXT_DIM,
                anchor="w"
            ).pack(fill="x", pady=(2, 0))

            del_btn = ctk.CTkButton(
                row,
                text="Tắt Khởi Động",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                fg_color="#7f1d1d",
                hover_color=COLOR_DANGER_HOVER,
                width=110,
                height=30,
                corner_radius=4,
                command=lambda item=it: self._handle_delete_startup_item(item)
            )
            del_btn.pack(side="right", padx=12)

    def _handle_delete_startup_item(self, item: dict):
        if messagebox.askyesno(
            "Xác Nhận",
            f"Bạn có chắc chắn muốn tắt khởi động cùng Windows cho ứng dụng:\n\n{item['name']}?"
        ):
            ok, msg = remove_startup_item(item["root"], item["key"], item["name"])
            self.log(msg)
            if ok:
                self._refresh_startup_items()
            else:
                messagebox.showerror("Lỗi", msg)

    # -------------------------------------------------------------
    # VIEW: NETWORK, DNS & RAM CACHE
    # -------------------------------------------------------------
    def _create_network_view(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")

        # Box 1: DNS Optimizer
        dns_box = ctk.CTkFrame(frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        dns_box.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            dns_box,
            text="🌐 Tối Ưu Hóa Tốc Độ Mạng & DNS An Toàn",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        ).pack(anchor="w", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            dns_box,
            text="Sử dụng DNS tốc độ cao giúp lướt web nhanh hơn, giảm ping khi chơi game và ngăn ngừa theo dõi từ nhà mạng ISP.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 12))

        btn_row = ctk.CTkFrame(dns_box, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkButton(
            btn_row,
            text="⚡ Cloudflare DNS (1.1.1.1)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            height=34,
            command=lambda: self._handle_apply_dns("Cloudflare")
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="🔍 Google DNS (8.8.8.8)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#0891b2",
            hover_color="#0e7490",
            height=34,
            command=lambda: self._handle_apply_dns("Google")
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row,
            text="🔄 Khôi Phục DNS Tự Động (DHCP)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#334155",
            hover_color="#475569",
            height=34,
            command=self._handle_reset_dns
        ).pack(side="left", padx=8)

        # Box 2: DNS Cache Flush
        flush_box = ctk.CTkFrame(frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        flush_box.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            flush_box,
            text="🧹 Xóa Bộ Nhớ Đệm DNS (Flush DNS Cache)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        ).pack(anchor="w", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            flush_box,
            text="Làm mới bộ nhớ đệm phân giải tên miền để sửa lỗi không truy cập được website hoặc sau khi đổi DNS.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 12))

        ctk.CTkButton(
            flush_box,
            text="Xóa Sạch DNS Cache Ngay",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            height=34,
            command=self._handle_flush_dns
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # Box 3: Safe Memory Trim
        ram_box = ctk.CTkFrame(frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
        ram_box.pack(fill="x")

        ctk.CTkLabel(
            ram_box,
            text="🚀 Giải Phóng Bộ Nhớ Đệm RAM (Safe Working Set Trim)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        ).pack(anchor="w", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            ram_box,
            text="Thu gọn bộ nhớ làm việc của các tiến trình không còn sử dụng về đĩa, trả lại bộ nhớ RAM vật lý tức thì một cách an toàn.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 12))

        ctk.CTkButton(
            ram_box,
            text="Giải Phóng Bộ Nhớ RAM Ngay",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#d97706",
            hover_color="#b45309",
            height=34,
            command=self._handle_trim_ram
        ).pack(anchor="w", padx=16, pady=(0, 14))

        return frame

    def _handle_apply_dns(self, provider: str):
        self.log(f"Đang cấu hình {provider} DNS...")
        def worker():
            ok, msg = set_primary_dns(provider)
            self.log(msg)
            self.after(0, lambda: messagebox.showinfo("Cấu Hình DNS", msg) if ok else messagebox.showerror("Lỗi DNS", msg))
        threading.Thread(target=worker, daemon=True).start()

    def _handle_reset_dns(self):
        self.log("Đang khôi phục DNS về mặc định DHCP...")
        def worker():
            ok, msg = reset_dns_to_dhcp()
            self.log(msg)
            self.after(0, lambda: messagebox.showinfo("Cấu Hình DNS", msg) if ok else messagebox.showerror("Lỗi DNS", msg))
        threading.Thread(target=worker, daemon=True).start()

    def _handle_flush_dns(self):
        ok, msg = flush_dns_cache()
        self.log(msg)
        if ok:
            messagebox.showinfo("DNS Cache", msg)
        else:
            messagebox.showerror("Lỗi", msg)

    def _handle_trim_ram(self):
        ok, msg = trim_memory_working_sets()
        self.log(msg)
        if ok:
            messagebox.showinfo("Tối Ưu RAM", msg)
        else:
            messagebox.showerror("Lỗi", msg)

