import logging
import os
from environs import Env

# Logging sozlamasi
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# environs kutubxonasidan foydalanish
env = Env()
env.read_env()

# .env fayl ichidan ma'lumotlarni o'qiymiz
BOT_TOKEN = env.str("BOT_TOKEN")
ADMINS = env.list("ADMINS", subcast=int, default=[])
IP = env.str("ip", default="localhost")


def update_env_admins(admins: list):
    """ADMINS ro'yxatini .env faylida yangilash (agar fayl mavjud bo'lsa)."""
    env_path = ".env"
    if not os.path.exists(env_path):
        logger.warning(".env fayli topilmadi, ADMINS faqat xotirada saqlandi (Docker rejimi).")
        return
    try:
        with open(env_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        with open(env_path, "w", encoding="utf-8") as file:
            for line in lines:
                if not line.strip().startswith("ADMINS="):
                    file.write(line)
            file.write(f"ADMINS={','.join(map(str, admins))}\n")
        global ADMINS
        env.read_env(override=True)
        ADMINS = env.list("ADMINS", subcast=int, default=[])
        logger.info(f".env yangilandi, ADMINS: {ADMINS}")
    except PermissionError:
        logger.error(".env fayliga yozish uchun ruxsat yo'q")
        raise
    except Exception as e:
        logger.error(f".env yangilashda xatolik: {e}")
        raise


logger.info(f"ADMINS: {ADMINS}")
logger.info(f"IP: {IP}")