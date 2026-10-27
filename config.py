from pathlib import Path

# Folder chứa EPUB
ROOT_FOLDER = Path(r"D:\Khanh\fugNovelpia")

# Nơi lưu report
REPORT_FOLDER = Path("reports")

# Nơi lưu log
LOG_FOLDER = Path("logs")

# Số thread
MAX_WORKERS = 8

# Bật/Tắt từng module kiểm tra
CHECK_HEADER = True
CHECK_ZIP = True
CHECK_STRUCTURE = True
CHECK_EBOOKLIB = True
CHECK_HTML = True
CHECK_IMAGE = True
CHECK_METADATA = True
CHECK_CALIBRE = False
CHECK_EPUBCHECK = False