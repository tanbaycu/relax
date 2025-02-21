import os
import telebot
import aiohttp
import asyncio
import random
import logging
from telebot.async_telebot import AsyncTeleBot
from deep_translator import GoogleTranslator
from io import BytesIO
from datetime import datetime
import certifi
import ssl

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Khởi tạo bot với token Telegram của bạn
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("Không tìm thấy TELEGRAM_BOT_TOKEN trong biến môi trường")

bot = AsyncTeleBot(API_TOKEN)

# Tạo SSL context với chứng chỉ của certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Từ điển lưu trữ các tác vụ gửi thông tin cho người dùng
thong_tin_tasks = {}

async def lay_thong_tin_ngau_nhien():
    nguon_thong_tin = [
        (
            "https://dog-api.kinduff.com/api/facts",
            lambda data: ("🐶 Sự thật thú vị về chó", data["facts"][0]),
        ),
        (
            "https://catfact.ninja/fact",
            lambda data: ("🐱 Bí mật đáng yêu về mèo", data["fact"]),
        ),
        (
            "http://numbersapi.com/random/trivia",
            lambda data: ("🔢 Điều thú vị về con số", data),
        ),
        (
            "https://uselessfacts.jsph.pl/random.json?language=en",
            lambda data: ("🤔 Sự thật vô dụng nhưng thú vị", data["text"]),
        ),
        (
            "https://official-joke-api.appspot.com/random_joke",
            lambda data: ("😂 Tiếu lâm", f"{data['setup']} {data['punchline']}"),
        ),
    ]
    random.shuffle(nguon_thong_tin)

    async with aiohttp.ClientSession() as session:
        for nguon, trich_xuat_du_lieu in nguon_thong_tin:
            try:
                async with session.get(nguon, ssl=ssl_context, timeout=10) as phan_hoi:
                    if phan_hoi.status == 200:
                        du_lieu = await phan_hoi.json(content_type=None)
                        tieu_de, noi_dung = trich_xuat_du_lieu(du_lieu)
                        return tieu_de, noi_dung
            except asyncio.TimeoutError:
                logger.warning(f"Timeout khi lấy dữ liệu từ {nguon}")
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu từ {nguon}: {str(e)}")
                continue

    return (
        "Không thể lấy thông tin",
        "Xin lỗi, tôi không thể lấy thông tin lúc này. Hãy thử lại sau nhé!",
    )

@bot.message_handler(commands=['start', 'help'])
async def gui_loi_chao(message):
    loi_chao = (
        "🌟 Chào mừng bạn đến với Trợ Lý Giải Trí được tanbaycu phát triển! 🌟\n\n"
        "Tôi có thể giúp bạn giải trí với những thông tin thú vị. Đây là danh sách lệnh của tôi:\n\n"
        "🔹 /thongtin - Nhận thông tin thú vị ngẫu nhiên\n"
        "🔹 /dungthongtin - Dừng nhận thông tin\n"
        "🔹 /trichdan - Nhận một trích dẫn ngẫu nhiên\n"
        "🔹 /hinhanh - Nhận một hình ảnh ngẫu nhiên\n"
        "🔹 /help - Hiển thị lại thông điệp này\n\n"
        "Hãy thử một lệnh và bắt đầu cuộc phiêu lưu giải trí nào! 😊"
    )
    await bot.reply_to(message, loi_chao)

@bot.message_handler(commands=['thongtin'])
async def thong_tin_ngau_nhien(message):
    user_id = str(message.from_user.id)
    if user_id in thong_tin_tasks:
        await bot.reply_to(message, "🔄 Bạn đang nhận thông tin rồi. Dùng /dungthongtin để dừng nhé!")
        return

    try:
        processing_msg = await bot.reply_to(message, "🔍 Đang tìm kiếm thông tin thú vị cho bạn...")
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn xử lý: {str(e)}")
        await bot.send_message(message.chat.id, "Có lỗi xảy ra khi bắt đầu tìm kiếm thông tin. Vui lòng thử lại sau.")
        return

    async def gui_thong_tin():
        while True:
            try:
                tieu_de, noi_dung = await lay_thong_tin_ngau_nhien()
                translator = GoogleTranslator(source="en", target="vi")
                noi_dung_dich = translator.translate(noi_dung)
                thoi_gian = datetime.now().strftime("%H:%M:%S")
                phan_hoi = (
                    f"🕒 {thoi_gian}\n\n"
                    f"📌 {tieu_de}\n\n"
                    f"🇬🇧 Tiếng Anh:\n{noi_dung}\n\n"
                    f"🇻🇳 Tiếng Việt:\n{noi_dung_dich}\n\n"
                    f"💡 Mẹo: Dùng /dungthongtin để dừng nhận thông tin."
                )
                try:
                    await bot.delete_message(message.chat.id, processing_msg.message_id)
                except Exception as delete_error:
                    logger.warning(f"Không thể xóa tin nhắn xử lý: {str(delete_error)}")
                
                await bot.send_message(message.chat.id, phan_hoi, parse_mode='Markdown')
                await asyncio.sleep(20)  # Gửi mỗi 20 giây
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông tin: {str(e)}")
                await bot.send_message(message.chat.id, "❌ Có lỗi xảy ra. Đang thử lại...")
                await asyncio.sleep(30)

    thong_tin_tasks[user_id] = asyncio.create_task(gui_thong_tin())
    logger.info(f"Bắt đầu gửi thông tin cho người dùng {message.from_user.username}")

@bot.message_handler(commands=['dungthongtin'])
async def dung_thong_tin(message):
    user_id = str(message.from_user.id)
    if user_id in thong_tin_tasks:
        thong_tin_tasks[user_id].cancel()
        del thong_tin_tasks[user_id]
        await bot.reply_to(message, "✅ Đã dừng gửi thông tin. Bạn có thể dùng /thongtin để bắt đầu lại bất cứ lúc nào!")
        logger.info(f"Đã dừng gửi thông tin cho người dùng {message.from_user.username}")
    else:
        await bot.reply_to(message, "❓ Bạn chưa bắt đầu nhận thông tin. Dùng /thongtin để bắt đầu nhé!")

@bot.message_handler(commands=['trichdan'])
async def trich_dan_ngau_nhien(message):
    nguon_trich_dan = [
        (
            "https://api.quotable.io/random",
            lambda data: (data["content"], data["author"], data.get("tags", [])),
        ),
        (
            "https://api.themotivate365.com/stoic-quote",
            lambda data: (data["quote"], data["author"], []),
        ),
        (
            "https://zenquotes.io/api/random",
            lambda data: (data[0]["q"], data[0]["a"], []),
        ),
        (
            "https://api.goprogram.ai/inspiration",
            lambda data: (data["quote"], data["author"], []),
        ),
    ]

    processing_msg = await bot.reply_to(message, "🔍 Đang tìm kiếm trích dẫn hay ho cho bạn...")

    async def fetch_quote(session, api, trich_xuat_du_lieu):
        try:
            async with session.get(api, ssl=ssl_context, timeout=10) as phan_hoi:
                if phan_hoi.status == 200:
                    du_lieu = await phan_hoi.json()
                    return api, trich_xuat_du_lieu(du_lieu)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout khi lấy trích dẫn từ {api}")
        except Exception as e:
            logger.error(f"Lỗi khi lấy trích dẫn từ {api}: {str(e)}")
        return None

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_quote(session, api, trich_xuat_du_lieu) for api, trich_xuat_du_lieu in nguon_trich_dan]
        ket_qua = await asyncio.gather(*tasks)
        
        for result in ket_qua:
            if result:
                api, (trich_dan, tac_gia, the) = result
                try:
                    translator = GoogleTranslator(source="en", target="vi")
                    trich_dan_dich = translator.translate(trich_dan)
                    tac_gia_dich = translator.translate(tac_gia)

                    phan_hoi = (
                        f"💬 Trích dẫn ngẫu nhiên\n\n"
                        f"🇬🇧 Tiếng Anh:\n\"{trich_dan}\"\n\n"
                        f"🇻🇳 Tiếng Việt:\n\"{trich_dan_dich}\"\n\n"
                        f"✍️ Tác giả:\n🇬🇧 {tac_gia} | 🇻🇳 {tac_gia_dich}\n"
                    )

                    if the:
                        phan_hoi += f"\n🏷️ Thẻ: {', '.join(the)}"

                    phan_hoi += f"\n\n📚 Nguồn: {api.split('//')[1].split('/')[0]}"

                    await bot.delete_message(message.chat.id, processing_msg.message_id)
                    await bot.reply_to(message, phan_hoi)
                    logger.info(f"Đã gửi trích dẫn ngẫu nhiên từ {api} cho người dùng {message.from_user.username}")
                    return
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý trích dẫn từ {api}: {str(e)}")

    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=processing_msg.message_id,
        text="😔 Xin lỗi, tôi không thể lấy trích dẫn lúc này. Hãy thử lại sau nhé!\n\n"
             "💡 Mẹo: Bạn có thể thử lại bằng cách gõ /trichdan một lần nữa."
    )
    logger.error("Không thể lấy trích dẫn từ tất cả các nguồn.")

@bot.message_handler(commands=['hinhanh'])
async def hinh_anh_ngau_nhien(message):
    nguon_hinh_anh = [
        ("https://source.unsplash.com/random", "Unsplash"),
        ("https://picsum.photos/500", "Lorem Picsum"),
        ("https://api.thecatapi.com/v1/images/search", "The Cat API"),
        ("https://dog.ceo/api/breeds/image/random", "Dog CEO"),
    ]

    processing_msg = await bot.reply_to(message, "🔍 Đang tìm kiếm hình ảnh đẹp cho bạn...")

    async with aiohttp.ClientSession() as session:
        for api, nguon in random.sample(nguon_hinh_anh, len(nguon_hinh_anh)):
            try:
                if "thecatapi" in api or "dog.ceo" in api:
                    async with session.get(api, ssl=ssl_context, timeout=10) as phan_hoi:
                        if phan_hoi.status == 200:
                            du_lieu = await phan_hoi.json()
                            url_hinh_anh = du_lieu[0]["url"] if "thecatapi" in api else du_lieu["message"]
                            async with session.get(url_hinh_anh, ssl=ssl_context, timeout=10) as phan_hoi_hinh:
                                if phan_hoi_hinh.status == 200:
                                    du_lieu_hinh = await phan_hoi_hinh.read()
                                    chu_thich = (
                                        f"🖼️ Hình ảnh ngẫu nhiên\n"
                                        f"📸 Nguồn: {nguon}\n"
                                        f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S')}\n"
                                        f"💡 Mẹo: Dùng /hinhanh để nhận hình ảnh mới!"
                                    )
                                    await bot.delete_message(message.chat.id, processing_msg.message_id)
                                    await bot.send_photo(message.chat.id, BytesIO(du_lieu_hinh), caption=chu_thich)
                                    logger.info(f"Đã gửi hình ảnh từ {nguon} cho người dùng {message.from_user.username}")
                                    return
                else:
                    async with session.get(api, ssl=ssl_context, timeout=10) as phan_hoi:
                        if phan_hoi.status == 200:
                            du_lieu_hinh = await phan_hoi.read()
                            chu_thich = (
                                f"🖼️ Hình ảnh ngẫu nhiên\n"
                                f"📸 Nguồn: {nguon}\n"
                                f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S')}\n"
                                f"💡 Mẹo: Dùng /hinhanh để nhận hình ảnh mới!"
                            )
                            await bot.delete_message(message.chat.id, processing_msg.message_id)
                            await bot.send_photo(message.chat.id, BytesIO(du_lieu_hinh), caption=chu_thich)
                            logger.info(f"Đã gửi hình ảnh từ {nguon} cho người dùng {message.from_user.username}")
                            return
            except asyncio.TimeoutError:
                logger.warning(f"Timeout khi lấy hình ảnh từ {api}")
            except Exception as e:
                logger.error(f"Lỗi khi tải hình ảnh từ {api}: {str(e)}")
                continue

    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=processing_msg.message_id,
        text="😔 Xin lỗi, tôi không thể lấy hình ảnh lúc này. Hãy thử lại sau nhé!\n\n"
             "💡 Mẹo: Bạn có thể thử lại bằng cách gõ /hinhanh một lần nữa."
    )
    logger.error("Không thể tải hình ảnh từ tất cả các nguồn.")

@bot.message_handler(commands=['retry_trichdan'])
async def thu_lai_trich_dan(message):
    await trich_dan_ngau_nhien(message)

@bot.message_handler(commands=['retry_hinhanh'])
async def thu_lai_hinh_anh(message):
    await hinh_anh_ngau_nhien(message)

if __name__ == "__main__":
    logger.info("Bot đang khởi động...")
    asyncio.run(bot.polling())
    logger.info("Bot đã dừng hoạt động.")