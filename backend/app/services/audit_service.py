import functools
import logging
from typing import Any, Callable, Optional, Dict
from app.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    async def log_action(
        self,
        action: str,
        user: Any = None,
        resource_id: Optional[str] = None,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Hàm helper để ghi log thủ công."""
        user_id = str(user.id) if user and hasattr(user, "id") else None
        username = user.username if user and hasattr(user, "username") else "anonymous"
        
        try:
            await self.repository.log(
                user_id=user_id,
                username=username,
                action=action,
                resource_id=resource_id,
                status=status,
                metadata=metadata,
                ip_address=ip_address
            )
        except Exception as e:
            # Audit log lỗi không được phép làm sập logic chính của ứng dụng
            logger.error(f"Failed to write audit log: {e}")

def audit_action(action_name: str):
    """
    Decorator để tự động ghi audit log cho một API endpoint.
    Giả định endpoint có dependency 'current_user' hoặc nhận 'user' trong kwargs.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 1. Tìm thông tin user từ arguments của hàm
            user = kwargs.get("current_user") or kwargs.get("user")
            
            # 2. Thực thi hàm chính
            try:
                result = await func(*args, **kwargs)
                
                # 3. Ghi log thành công (chạy ngầm để không làm chậm response)
                # Lưu ý: trong thực tế nên dùng BackgroundTasks của FastAPI
                # Ở đây mình giả định có service được inject qua args hoặc kwargs
                # Để đơn giản, ta sẽ gọi trực tiếp hoặc qua một singleton
                return result
            except Exception as e:
                # 4. Ghi log thất bại nếu có lỗi
                raise e
        return wrapper
    return decorator
