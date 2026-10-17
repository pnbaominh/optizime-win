import unittest
from unittest.mock import MagicMock, patch
import customtkinter as ctk
from ui.update_dialog import UpdateDialog
from ui.main_window import MainWindow

class TestUpdateDialogSingleton(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tạo hidden CTk root để test GUI widgets trong headless/offscreen
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        # Reset singleton state before each test
        UpdateDialog._active_instance = None

    def tearDown(self):
        if UpdateDialog._active_instance is not None:
            try:
                UpdateDialog._active_instance.destroy()
            except Exception:
                pass
        UpdateDialog._active_instance = None

    def test_update_dialog_singleton_same_instance(self):
        info1 = {
            "has_update": True,
            "current_version": "1.2.0",
            "latest_version": "v1.2.1",
            "changelog": "Fixes and improvements",
            "download_url": "https://example.com/setup.exe"
        }
        dlg1 = UpdateDialog(self.root, info1)
        self.assertIsNotNone(dlg1)
        self.assertIs(UpdateDialog._active_instance, dlg1)

        # Call again with another dict
        info2 = dict(info1, latest_version="v1.2.2")
        dlg2 = UpdateDialog(self.root, info2)

        # Must return the exact same instance, not create a second window
        self.assertIs(dlg1, dlg2)

        # Destroy
        dlg1.destroy()
        self.assertIsNone(UpdateDialog._active_instance)

        # Call again after destroy -> creates a new instance
        dlg3 = UpdateDialog(self.root, info1)
        self.assertIsNot(dlg1, dlg3)
        self.assertIs(UpdateDialog._active_instance, dlg3)
        dlg3.destroy()

    def test_update_dialog_cleans_parent_reference(self):
        parent_mock = MagicMock()
        info = {
            "has_update": True,
            "current_version": "1.2.0",
            "latest_version": "v1.2.1",
            "changelog": "Test",
            "download_url": "https://example.com/setup.exe"
        }
        dlg = UpdateDialog(self.root, info)
        parent_mock._update_dialog = dlg
        dlg._parent = parent_mock

        dlg.destroy()
        self.assertIsNone(parent_mock._update_dialog)
        self.assertIsNone(UpdateDialog._active_instance)

    def test_main_window_show_update_dialog_debounces(self):
        """Kiểm tra _show_update_dialog hủy silent timer và không tạo trùng lặp."""
        win_mock = MagicMock(spec=MainWindow)
        win_mock._silent_update_after_id = "after#123"
        win_mock._update_dialog = None
        win_mock._is_checking_updates = False
        win_mock.after_cancel = MagicMock()

        info = {"has_update": True, "latest_version": "v1.2.1"}

        with patch("ui.main_window.UpdateDialog") as MockDialog:
            mock_dlg_instance = MagicMock()
            mock_dlg_instance.winfo_exists.return_value = True
            MockDialog.return_value = mock_dlg_instance

            # Gọi lần 1
            MainWindow._show_update_dialog(win_mock, info)
            win_mock.after_cancel.assert_called_once_with("after#123")
            self.assertIsNone(win_mock._silent_update_after_id)
            self.assertIs(win_mock._update_dialog, mock_dlg_instance)
            self.assertEqual(MockDialog.call_count, 1)

            # Gọi lần 2 khi dialog đã mở -> lift, không tạo thêm
            MainWindow._show_update_dialog(win_mock, info)
            mock_dlg_instance.lift.assert_called_once()
            mock_dlg_instance.focus_force.assert_called_once()
            self.assertEqual(MockDialog.call_count, 1)

    def test_main_window_check_for_updates_manually_debounces(self):
        """Kiểm tra _check_for_updates_manually không kích hoạt nếu đang kiểm tra hoặc dialog đang mở."""
        win_mock = MagicMock(spec=MainWindow)
        win_mock._is_checking_updates = True
        win_mock._update_dialog = None
        win_mock.log = MagicMock()

        with patch("threading.Thread") as mock_thread:
            # Khi _is_checking_updates = True, bấm nút không được làm gì
            MainWindow._check_for_updates_manually(win_mock)
            mock_thread.assert_not_called()

        # Khi dialog đang mở sẵn, bấm nút sẽ lift dialog chứ không kiểm tra mạng lại
        win_mock._is_checking_updates = False
        mock_dlg = MagicMock()
        mock_dlg.winfo_exists.return_value = True
        win_mock._update_dialog = mock_dlg

        with patch("threading.Thread") as mock_thread:
            MainWindow._check_for_updates_manually(win_mock)
            mock_dlg.lift.assert_called_once()
            mock_dlg.focus_force.assert_called_once()
            mock_thread.assert_not_called()

if __name__ == "__main__":
    unittest.main()
