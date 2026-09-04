"""
AI bilan ishlash uchun yordamchi funksiyalar.
Grok (xAI) API ishlatiladi — u OpenAI SDK bilan to'liq mos (compatible),
shuning uchun faqat base_url xAI serveriga yo'naltirilgan.
"""
import json
import re
from openai import OpenAI
from config import GROK_API_KEY, GROK_BASE_URL, AI_MODEL

client = OpenAI(api_key=GROK_API_KEY, base_url=GROK_BASE_URL)


def ask_question(question: str) -> str:
    """Foydalanuvchi savoliga AI orqali javob qaytaradi (savol-javob bo'limi uchun)."""
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Siz foydali va bilimdon yordamchisiz. Foydalanuvchi savollariga "
                    "o'zbek tilida, aniq, tushunarli va qisqa-lo'nda javob bering. "
                    "Agar savol boshqa tilda bo'lsa, o'sha tilda javob bering."
                ),
            },
            {"role": "user", "content": question},
        ],
        temperature=0.5,
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()


def generate_referat(mavzu: str) -> dict:
    """
    Berilgan mavzu bo'yicha referat matnini generatsiya qiladi.
    Natija: {"kirish": str, "asosiy_qism": str, "xulosa": str, "adabiyotlar": str}
    """
    prompt = f"""Quyidagi mavzuda o'zbek tilida ilmiy referat matnini tayyorla: "{mavzu}"

Javobni AYNAN quyidagi formatda, har bir bo'limni katta harflar bilan yozilgan
sarlavha va ":" belgisidan keyin matn bilan ber. Boshqa hech qanday qo'shimcha
matn, izoh yoki markdown belgilarini ishlatma:

KIRISH:
(bu yerga kirish qismi matni, kamida 2-3 paragraf)

ASOSIY_QISM:
(bu yerga mavzuning asosiy mazmuni, kamida 4-6 paragraf, batafsil va mazmunli)

XULOSA:
(bu yerga xulosa qismi, 1-2 paragraf)

ADABIYOTLAR:
(bu yerga 4-6 ta foydalanilgan adabiyot ro'yxati, har biri yangi qatorda, raqamlangan)
"""
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Siz ilmiy referat yozish bo'yicha mutaxassissiz. Faqat so'ralgan formatda javob bering.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=3000,
    )
    text = response.choices[0].message.content.strip()
    return _parse_referat(text)


def _parse_referat(text: str) -> dict:
    sections = {"kirish": "", "asosiy_qism": "", "xulosa": "", "adabiyotlar": ""}
    pattern = r"(KIRISH|ASOSIY_QISM|XULOSA|ADABIYOTLAR):\s*(.*?)(?=(?:KIRISH|ASOSIY_QISM|XULOSA|ADABIYOTLAR):|$)"
    matches = re.findall(pattern, text, re.DOTALL)
    key_map = {
        "KIRISH": "kirish",
        "ASOSIY_QISM": "asosiy_qism",
        "XULOSA": "xulosa",
        "ADABIYOTLAR": "adabiyotlar",
    }
    for key, content in matches:
        sections[key_map[key]] = content.strip()

    # Agar parsing muvaffaqiyatsiz bo'lsa, hammasini asosiy qismga qo'yamiz
    if not any(sections.values()):
        sections["asosiy_qism"] = text
    return sections


def generate_presentation_outline(mavzu: str, slide_count: int = 8) -> dict:
    """
    Prezentatsiya uchun slaydlar tuzilmasini JSON ko'rinishida generatsiya qiladi.
    Natija: {"title": str, "slides": [{"title": str, "bullets": [str, ...]}, ...]}
    """
    prompt = f"""Quyidagi mavzuda o'zbek tilida taqdimot (prezentatsiya) tuzilmasini tayyorla: "{mavzu}"

Jami {slide_count} ta slayd bo'lsin (birinchisi sarlavha slaydi). Faqat va faqat
quyidagi JSON formatida javob ber, boshqa hech qanday matn, izoh yoki markdown
belgilarini (```) qo'shma:

{{
  "title": "Taqdimot sarlavhasi",
  "subtitle": "Qisqa tavsif yoki muallif uchun joy",
  "slides": [
    {{"title": "Slayd sarlavhasi", "bullets": ["Fikr 1", "Fikr 2", "Fikr 3"]}}
  ]
}}

Har bir slaydda 3-5 ta qisqa va mazmunli bullet point bo'lsin.
"""
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Siz taqdimot tuzish bo'yicha mutaxassissiz. Faqat toza JSON qaytaring.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=2500,
    )
    text = response.choices[0].message.content.strip()
    return _parse_json_outline(text, mavzu)


def _parse_json_outline(text: str, fallback_title: str) -> dict:
    # ```json ... ``` qobiqlarini tozalash
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
        if "slides" in data and isinstance(data["slides"], list):
            return data
    except json.JSONDecodeError:
        pass

    # Zaxira variant: oddiy matn strukturasi
    return {
        "title": fallback_title,
        "subtitle": "",
        "slides": [
            {"title": "Kirish", "bullets": ["Mavzu haqida umumiy ma'lumot"]},
            {"title": "Xulosa", "bullets": [text[:300]]},
        ],
    }


# ---------------------------------------------------------------------------
# Boshqa Grok modellariga o'tish uchun .env dagi AI_MODEL qiymatini
# o'zgartiring, masalan: "grok-4-fast", "grok-4", "grok-3", "grok-3-mini".
# Mavjud modellar ro'yxati: https://docs.x.ai/docs/models
#
# OpenAI'ga qaytmoqchi bo'lsangiz: config.py dagi GROK_API_KEY/GROK_BASE_URL
# o'rniga OPENAI_API_KEY qo'shing va yuqoridagi client qatorini
#   client = OpenAI(api_key=OPENAI_API_KEY)
# ga o'zgartiring (base_url kerak emas).
# ---------------------------------------------------------------------------
