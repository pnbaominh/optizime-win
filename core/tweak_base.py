from abc import ABC, abstractmethod
from typing import Tuple

class Tweak(ABC):
    """
    Lớp cơ sở trừu tượng cho mọi tùy chọn tối ưu hóa.
    Mỗi tùy chọn BẮT BUỘC phải cài đặt 3 phương thức:
    - check(): Kiểm tra trạng thái thực tế từ Registry hoặc Service của Windows.
    - apply(): Thực hiện tinh chỉnh thực tế (kèm sao lưu).
    - revert(): Đưa giá trị trở về nguyên bản 100%.
    """
    def __init__(
        self,
        tweak_id: str,
        name: str,
        category: str,
        description: str,
        explanation: str,
        is_recommended: bool = True,
        is_dangerous: bool = False
    ):
        self.id = tweak_id
        self.name = name
        self.category = category
        self.description = description
        self.explanation = explanation
        self.is_recommended = is_recommended
        self.is_dangerous = is_dangerous

    @abstractmethod
    def check(self) -> bool:
        """Trả về True nếu tinh chỉnh đang được áp dụng, False nếu đang ở mặc định."""
        pass

    @abstractmethod
    def apply(self) -> Tuple[bool, str]:
        """Áp dụng tinh chỉnh thực tế vào Windows. Trả về (Thành công, Thông báo)."""
        pass

    @abstractmethod
    def revert(self) -> Tuple[bool, str]:
        """Hoàn tác tinh chỉnh về thiết lập mặc định của Windows. Trả về (Thành công, Thông báo)."""
        pass

    def to_dict(self) -> dict:
        """Chuyển đổi thông tin tweak thành dictionary để hiển thị trên UI."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "explanation": self.explanation,
            "is_recommended": self.is_recommended,
            "is_dangerous": self.is_dangerous,
            "is_applied": self.check()
        }
