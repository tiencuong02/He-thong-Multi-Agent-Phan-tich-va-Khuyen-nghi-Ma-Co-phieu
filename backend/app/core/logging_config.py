import logging
import sys
from asgi_correlation_id import CorrelationIdFilter

def setup_logging():
    """
    Cấu hình logging tập trung cho toàn bộ hệ thống.
    Thêm filter CorrelationIdFilter để tự động chèn request_id vào mỗi dòng log.
    """
    # 1. Định nghĩa format cho log: [Thời gian] [Level] [Request_ID] [Tên file:Dòng] Tin nhắn
    log_format = (
        "%(asctime)s - %(levelname)s - [%(correlation_id)s] - %(name)s:%(lineno)d - %(message)s"
    )

    # 2. Tạo filter để lấy correlation_id từ context của request
    cid_filter = CorrelationIdFilter(uuid_length=8) # Lấy 8 ký tự cho ngắn gọn

    # 3. Cấu hình root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format))
    handler.addFilter(cid_filter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True # Ghi đè cấu hình cũ nếu có
    )

    # Giảm bớt log rác từ các thư viện ngoài
    logging.getLogger("uvicorn.access").addFilter(cid_filter)
    logging.getLogger("uvicorn.error").addFilter(cid_filter)
