import asyncio
import json
import os
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import re

# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN_CONSTRUCTION", "ВСТАВЬ_СВОЙ_ТОКЕН")
TELEGRAM_CHAT_IDS = ["248752467", "6522826404"] # добавь ID друга если нужно

KEYWORDS = [
    # Русские — точные названия позиций
    "технический консультант строительства",
    "ведущий инженер строительный консалтинг",
    "инженер технического надзора",
    "старший консультант в строительстве",
    "технический надзор в строительстве",
    "строительный консалтинг",
    "консультант инфраструктурных проектов",
    "менеджер инфраструктурных проектов",
    "руководитель инфраструктурных проектов",
    "технический менеджер проекта по строительству",
    "инженер по строительному консалтингу",
    # Английские
    "construction consultant", "construction project consultant",
    "construction project manager", "construction advisory",
    "building consultant", "real estate consultant",
    "infrastructure consultant", "capital projects consultant",
    "construction manager", "project consultant construction",
    "advisory construction", "consulting construction",
    "PWC construction", "big4 construction",
    "technical advisor construction", "owner representative",
    # Big 4 / Big 5
    "PwC infrastructure", "PwC construction", "PwC capital projects",
    "Deloitte infrastructure", "Deloitte construction", "Deloitte real estate",
    "KPMG infrastructure", "KPMG construction", "KPMG capital projects",
    "EY infrastructure", "EY construction", "EY real estate advisory",
    "McKinsey infrastructure", "McKinsey capital projects",
    "BCG infrastructure", "Bain infrastructure",
    "big4 infrastructure", "big 4 infrastructure",
    "advisory infrastructure", "advisory capital projects",
    "associate infrastructure advisory", "senior associate infrastructure advisory",
    "manager infrastructure advisory", "consultant infrastructure advisory",
    "associate real estate advisory", "associate capital projects",
    "transaction advisory construction", "transaction services infrastructure",
    "financial advisory infrastructure", "strategy infrastructure",
    # Новые
    "technical auditor", "project auditor",
    "technical advisor", "technical due diligence",
    "TDD", "technical due diligence construction",
    "senior associate infrastructure", "infrastructure project",
    "технический аудитор", "технический аудит проекта",
    "аудит строительного проекта", "технический советник",
    "технический консультант проект", "due diligence строительство",
    "технический due diligence", "старший консультант инфраструктура",
]

EXCLUDE_LOCATIONS = [
    "united states", "usa", "u.s.", "u.s.a",
    "new york", "san francisco", "los angeles", "chicago", "seattle",
    "austin", "boston", "denver", "miami", "atlanta",
    "houston", "dallas", "phoenix", "philadelphia", "san diego",
    ", al", ", ak", ", az", ", ar", ", ca", ", co", ", ct", ", de",
    ", fl", ", ga", ", hi", ", id", ", il", ", in", ", ia", ", ks",
    ", ky", ", la", ", me", ", md", ", ma", ", mi", ", mn", ", ms",
    ", mo", ", mt", ", ne", ", nv", ", nh", ", nj", ", nm", ", ny",
    ", nc", ", nd", ", oh", ", ok", ", or", ", pa", ", ri", ", sc",
    ", sd", ", tn", ", tx", ", ut", ", vt", ", va", ", wa", ", wv",
    ", wi", ", wy", ", dc"
]

RUSSIA_LOCATIONS = [
    "россия", "russia",
    # Крупнейшие города
    "москва", "moscow", "санкт-петербург", "saint-petersburg", "спб",
    "екатеринбург", "новосибирск", "казань", "нижний новгород",
    "челябинск", "самара", "омск", "ростов-на-дону", "ростов",
    "уфа", "красноярск", "воронеж", "пермь", "краснодар",
    # Средние города
    "волгоград", "саратов", "тюмень", "тольятти", "ижевск",
    "барнаул", "ульяновск", "иркутск", "хабаровск", "владивосток",
    "ярославль", "махачкала", "томск", "оренбург", "кемерово",
    "новокузнецк", "рязань", "астрахань", "пенза", "липецк",
    "тула", "киров", "чебоксары", "калининград", "брянск",
    "курск", "иваново", "магнитогорск", "тверь", "ставрополь",
    "белгород", "нижний тагил", "архангельск", "мурманск", "сочи",
    "владикавказ", "грозный", "улан-удэ", "якутск", "чита",
    "сургут", "нижневартовск", "череповец", "вологда", "смоленск",
    "калуга", "орёл", "владимир", "кострома", "тамбов",
    "нальчик", "майкоп", "элиста", "абакан", "кызыл",
]

# Стоп-слова в названии вакансии — исключаем сразу
TITLE_STOP_WORDS = [
    "продавец", "менеджер по продажам", "торговый", "sales",
    "прораб", "монтажник", "сварщик", "электрик", "слесарь",
    "водитель", "кладовщик", "грузчик", "разнорабочий",
    "дизайнер интерьера", "сметчик", "снабжение",
]

REMOTE_MARKERS = [
    "удалённо", "удаленно", "дистанционно", "remote", "fully remote",
    "100% remote", "work from anywhere", "worldwide", "anywhere",
    "из любой точки", "из любой страны", "home office", "wfh",
]

SALARY_MIN = {"USD": 2000, "EUR": 2000, "RUR": 300000, "KZT": 1000000}

# Азиатские локации для фильтра
# Азия и Ближний Восток — /mode_asia
ASIA_LOCATIONS = [
    # Ближний Восток
    "dubai", "abu dhabi", "uae", "united arab emirates",
    "дубай", "абу-даби", "оаэ",
    "saudi arabia", "riyadh", "jeddah", "ksa",
    "саудовская аравия", "эр-рияд", "джидда",
    "qatar", "doha", "катар", "доха",
    "kuwait", "кувейт",
    # Азия
    "singapore", "сингапур",
    "china", "beijing", "shanghai", "shenzhen",
    "китай", "пекин", "шанхай",
    "thailand", "bangkok", "таиланд", "бангкок",
    "vietnam", "ho chi minh", "hanoi", "вьетнам",
    "malaysia", "kuala lumpur", "малайзия", "куала-лумпур",
    "philippines", "manila", "филиппины", "манила",
]

# СНГ + Восточная Европа — /mode_cis_eu
CIS_EU_LOCATIONS = [
    "georgia", "tbilisi", "батуми", "грузия", "тбилиси",
    "armenia", "yerevan", "ереван", "армения",
    "poland", "warsaw", "krakow", "польша", "варшава", "краков",
    "latvia", "riga", "латвия", "рига",
    "lithuania", "vilnius", "литва", "вильнюс",
    "serbia", "belgrade", "novi sad", "сербия", "белград", "нови сад",
    "cyprus", "nicosia", "limassol", "кипр", "никосия", "лимасол",
]

# Ключевые слова для азиатских вакансий (доп. к основным)
ASIA_KEYWORDS = [
    "construction consultant dubai", "construction consultant uae",
    "construction consultant qatar", "construction consultant saudi",
    "construction consultant singapore", "construction consultant asia",
    "infrastructure consultant dubai", "infrastructure consultant uae",
    "technical advisor dubai", "technical advisor uae",
    "project manager construction dubai", "project manager construction doha",
    "capital projects dubai", "capital projects riyadh",
    "PwC dubai construction", "Deloitte dubai construction",
    "KPMG dubai infrastructure", "EY dubai infrastructure",
]

CHECK_INTERVAL = 7200  # каждые 2 часа
SEEN_FILE = "seen_jobs_construction.json"

MODE_ALL = "all"
MODE_NO_RUSSIA = "no_russia"
MODE_REMOTE_ONLY = "remote_only"
MODE_ASIA = "asia"  # Ближний Восток + Азия
MODE_CIS_EU = "cis_eu"  # Грузия, Армения, Польша, Латвия, Литва, Сербия

current_mode = os.environ.get("MODE_CONSTRUCTION", MODE_ALL)
is_paused = False
# ============================================================

def is_usa(location):
    loc = location.lower()
    return any(excl in loc for excl in EXCLUDE_LOCATIONS)

def is_russian_text(title):
    return bool(re.search(r'[а-яА-ЯёЁ]', title))

def is_russia_location(area):
    return any(loc in area.lower() for loc in RUSSIA_LOCATIONS)

def is_office_schedule(schedule):
    return any(s in schedule.lower() for s in ["полный день", "сменный", "вахтовый"])

def is_asia_location(area, full_text):
    combined = f"{area} {full_text}".lower()
    return any(loc in combined for loc in ASIA_LOCATIONS)

def is_cis_eu_location(area, full_text):
    combined = f"{area} {full_text}".lower()
    return any(loc in combined for loc in CIS_EU_LOCATIONS)

def has_stop_word(title):
    t = title.lower()
    return any(w in t for w in TITLE_STOP_WORDS)

def is_remote_worldwide(area, schedule, text):
    combined = f"{area} {schedule} {text}".lower()
    return any(m in combined for m in REMOTE_MARKERS)

def salary_ok(salary):
    if not salary:
        return True
    currency = salary.get("currency", "").upper()
    amount = salary.get("from") or salary.get("to") or 0
    min_sal = SALARY_MIN.get(currency)
    if min_sal is None:
        return True
    return amount >= min_sal

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

async def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        for chat_id in TELEGRAM_CHAT_IDS:
            try:
                await client.post(url, json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False
                })
            except Exception as e:
                print(f"Ошибка отправки для {chat_id}: {e}")

def format_job(job):
    flag = "🇷🇺 " if job.get("is_russian") else ""
    lines = [f"{flag}<b>{job['title']}</b>"]
    if job.get("employer"):
        lines.append(f"🏢 {job['employer']}")
    if job.get("location"):
        lines.append(f"📍 {job['location']}")
    if job.get("salary"):
        lines.append(f"💰 {job['salary']}")
    lines.append(f"🔗 <a href='{job['link']}'>{job['source']}</a>")
    return "\n".join(lines)

async def fetch_hh(seen, mode):
    jobs = []

    searches = [
        # Русские — точные запросы
        {"text": "технический консультант строительство"},
        {"text": "ведущий инженер строительный консалтинг"},
        {"text": "инженер технический надзор строительство"},
        {"text": "старший консультант строительство"},
        {"text": "строительный консалтинг консультант"},
        {"text": "менеджер инфраструктурных проектов"},
        # Английские
        {"text": "construction consultant"},
        {"text": "construction project manager"},
        {"text": "capital projects consultant"},
        {"text": "construction advisory"},
        {"text": "technical auditor construction"},
        {"text": "technical advisor infrastructure"},
        {"text": "project auditor construction"},
        {"text": "technical due diligence"},
        {"text": "senior associate infrastructure"},
        # Азия
        {"text": "construction consultant Dubai"},
        {"text": "construction consultant UAE"},
        {"text": "construction consultant Qatar"},
        {"text": "infrastructure consultant Dubai"},
        {"text": "technical advisor Dubai"},
        {"text": "capital projects Dubai"},
        {"text": "construction manager Singapore"},
        {"text": "технический консультант Казахстан"},
        {"text": "строительный консалтинг Казахстан"},
        {"text": "технический консультант Ташкент"},
        # Big 4 / Big 5
        {"text": "PwC infrastructure"},
        {"text": "Deloitte infrastructure"},
        {"text": "KPMG infrastructure"},
        {"text": "EY infrastructure"},
        {"text": "McKinsey infrastructure"},
        {"text": "advisory capital projects"},
        {"text": "transaction advisory infrastructure"},
        {"text": "consultant infrastructure advisory"},
    ]

    async with httpx.AsyncClient(timeout=20) as client:
        for search in searches:
            try:
                params = {
                    "text": search["text"],
                    "per_page": 50,
                    "order_by": "publication_time",
                    "search_field": "name",
                }
                if "schedule" in search:
                    params["schedule"] = search["schedule"]

                resp = await client.get(
                    "https://api.hh.ru/vacancies",
                    params=params,
                    headers={"User-Agent": "job-monitor/1.0"}
                )
                if resp.status_code != 200:
                    continue

                for item in resp.json().get("items", []):
                    job_id = f"hh_{item['id']}"
                    if job_id in seen:
                        continue

                    title = item.get("name", "")
                    employer = item.get("employer", {}).get("name", "")
                    link = item.get("alternate_url", "")
                    salary = item.get("salary")
                    schedule = item.get("schedule", {}).get("name", "") or ""
                    area = item.get("area", {}).get("name", "") or ""
                    snippet = item.get("snippet", {})
                    full_text = f"{title} {snippet.get('requirement', '') or ''} {snippet.get('responsibility', '') or ''}"
                    location_str = f"{area} · {schedule}".strip(" ·")

                    if has_stop_word(title):
                        continue
                    if is_usa(location_str):
                        continue
                    if is_russia_location(area) and is_office_schedule(schedule):
                        continue
                    if mode == MODE_NO_RUSSIA and is_russia_location(area):
                        continue
                    if mode == MODE_REMOTE_ONLY and not is_remote_worldwide(area, schedule, full_text):
                        continue
                    if mode == MODE_ASIA and not is_asia_location(area, full_text):
                        continue
                    if mode == MODE_CIS_EU and not is_cis_eu_location(area, full_text):
                        continue
                    if not salary_ok(salary):
                        continue

                    salary_str = ""
                    if salary:
                        frm = salary.get("from")
                        to = salary.get("to")
                        cur = salary.get("currency", "")
                        if frm and to:
                            salary_str = f"{frm}–{to} {cur}"
                        elif frm:
                            salary_str = f"от {frm} {cur}"
                        elif to:
                            salary_str = f"до {to} {cur}"

                    jobs.append({
                        "id": job_id, "source": "hh.ru", "title": title,
                        "employer": employer, "salary": salary_str,
                        "location": location_str, "link": link,
                        "is_russian": is_russian_text(title)
                    })
                    seen.add(job_id)

                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Ошибка hh.ru '{search.get('text')}': {e}")

    return jobs

# LinkedIn geoId коды стран
LINKEDIN_GEO = {
    "uae":       "104305776",
    "qatar":     "104305776",  # используем UAE как базу для Залива
    "saudi":     "101004012",
    "singapore": "102454443",
    "georgia":   "106093601",
    "armenia":   "102669407",
    "poland":    "105072130",
    "latvia":    "102974008",
    "lithuania": "101464403",
    "serbia":    "101855366",
    "cyprus":    "104246216",
    "kazakhstan":"104289538",
    "remote":    "",           # без привязки к стране
}

async def fetch_linkedin(seen, period_seconds=86400, remote_only=False, mode=MODE_ALL):
    jobs = []

    # Базовые запросы с geoId по нужным странам
    # Формат: (keywords, geoId, label)
    if mode == MODE_ASIA:
        geo_queries = [
            ("construction+consultant", "104305776", "UAE"),
            ("infrastructure+consultant", "104305776", "UAE"),
            ("technical+advisor", "104305776", "UAE"),
            ("capital+projects", "101004012", "Saudi Arabia"),
            ("construction+advisory", "101004012", "Saudi Arabia"),
            ("construction+consultant", "102454443", "Singapore"),
            ("infrastructure+consultant", "102454443", "Singapore"),
            ("technical+due+diligence", "104305776", "UAE"),
        ]
    elif mode == MODE_CIS_EU:
        geo_queries = [
            # Грузия
            ("construction+consultant", "106093601", "Georgia"),
            ("technical+advisor+infrastructure", "106093601", "Georgia"),
            # Армения
            ("construction+consultant", "102669407", "Armenia"),
            ("infrastructure+consultant", "102669407", "Armenia"),
            # Польша — только 1 запрос чтобы не доминировала
            ("construction+consultant", "105072130", "Poland"),
            # Сербия
            ("construction+consultant", "101855366", "Serbia"),
            ("infrastructure+consultant", "101855366", "Serbia"),
            # Латвия
            ("construction+consultant", "102974008", "Latvia"),
            ("technical+advisor", "102974008", "Latvia"),
            # Литва
            ("construction+consultant", "101464403", "Lithuania"),
            # Кипр
            ("construction+consultant", "104246216", "Cyprus"),
            ("technical+due+diligence", "104246216", "Cyprus"),
        ]
    elif remote_only:
        geo_queries = [
            ("construction+consultant+remote", "", "Remote"),
            ("capital+projects+consultant+remote", "", "Remote"),
            ("technical+advisor+infrastructure+remote", "", "Remote"),
            ("construction+advisory+remote", "", "Remote"),
        ]
    else:
        # mode_all и mode_norussia — широкий поиск по всем регионам
        geo_queries = [
            ("construction+consultant", "104305776", "UAE"),
            ("construction+consultant", "101004012", "Saudi Arabia"),
            ("construction+consultant", "102454443", "Singapore"),
            ("construction+consultant", "106093601", "Georgia"),
            ("construction+consultant", "105072130", "Poland"),
            ("infrastructure+consultant", "104305776", "UAE"),
            ("technical+due+diligence", "104305776", "UAE"),
            ("capital+projects+consultant", "101004012", "Saudi Arabia"),
            ("PwC+infrastructure", "104305776", "UAE"),
            ("Deloitte+infrastructure", "104305776", "UAE"),
            ("KPMG+infrastructure", "102454443", "Singapore"),
            ("construction+consultant", "101855366", "Serbia"),
            ("construction+consultant", "104246216", "Cyprus"),
            ("construction+consultant+remote", "", "Remote"),
        ]

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for keywords, geo_id, label in geo_queries:
            try:
                geo_param = f"&geoId={geo_id}" if geo_id else ""
                wt = "&f_WT=2" if remote_only else ""
                url = (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={keywords}{geo_param}{wt}"
                    f"&f_TPR=r{period_seconds}&sortBy=DD"
                )
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                })
                soup = BeautifulSoup(resp.text, "html.parser")
                for card in soup.find_all("div", class_=re.compile("job-search-card|base-card"))[:15]:
                    try:
                        title_el = card.find("h3")
                        company_el = card.find("h4")
                        link_el = card.find("a", href=True)
                        location_el = card.find("span", class_=re.compile("location|job-search-card__location"))
                        if not title_el or not link_el:
                            continue
                        title = title_el.get_text(strip=True)
                        company = company_el.get_text(strip=True) if company_el else ""
                        link = link_el["href"].split("?")[0]
                        location = location_el.get_text(strip=True) if location_el else label

                        loc_lower = location.lower()
                        if is_usa(location):
                            continue
                        if "united states" in loc_lower or ", us" in loc_lower:
                            continue
                        # Для mode_cis_eu — строгий whitelist по локации
                        if mode == MODE_CIS_EU and location and not is_cis_eu_location("", location):
                            continue
                        # Для mode_asia — строгий whitelist по локации
                        if mode == MODE_ASIA and location and not is_asia_location("", location):
                            continue

                        job_id = f"li_{abs(hash(link))}"
                        if job_id in seen:
                            continue
                        jobs.append({
                            "id": job_id, "source": f"LinkedIn ({label})",
                            "title": title, "employer": company,
                            "salary": "", "location": location or label,
                            "link": link, "is_russian": is_russian_text(title)
                        })
                        seen.add(job_id)
                    except Exception:
                        continue
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Ошибка LinkedIn '{label}': {e}")

    return jobs

async def send_jobs(jobs):
    if jobs:
        jobs.sort(key=lambda j: (0 if j.get("is_russian") else 1))
        await send_telegram(
            f"🏗 <b>Вакансии: Консультант по строительным проектам</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"Найдено: {len(jobs)}\n"
            f"🇷🇺 На русском: {sum(1 for j in jobs if j.get('is_russian'))}"
        )
        for job in jobs:
            await send_telegram(format_job(job))
            await asyncio.sleep(0.5)
    else:
        await send_telegram("🤷 Новых вакансий не найдено")

async def run_check():
    global current_mode, is_paused
    if is_paused:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] На паузе")
        return
    seen = load_seen()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Проверяю... режим: {current_mode}")
    remote_only = current_mode == MODE_REMOTE_ONLY
    hh_jobs = await fetch_hh(seen, current_mode)
    li_jobs = await fetch_linkedin(seen, 86400, remote_only, current_mode)
    print(f"hh.ru: {len(hh_jobs)}, LinkedIn: {len(li_jobs)}")
    await send_jobs(hh_jobs + li_jobs)
    save_seen(seen)

async def run_refresh():
    global current_mode, is_paused
    if is_paused:
        await send_telegram("⏸ Бот на паузе. Сначала напиши /resume")
        return
    await send_telegram("🔄 Обновляю подборку за последние 4 дня...")
    if os.path.exists(SEEN_FILE):
        os.remove(SEEN_FILE)
    seen = set()
    remote_only = current_mode == MODE_REMOTE_ONLY
    hh_jobs = await fetch_hh(seen, current_mode)
    li_jobs = await fetch_linkedin(seen, 345600, remote_only, current_mode)
    await send_jobs(hh_jobs + li_jobs)
    save_seen(seen)

async def poll_commands():
    global current_mode, is_paused
    offset = None
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            try:
                params = {"timeout": 10}
                if offset:
                    params["offset"] = offset
                resp = await client.get(url, params=params)
                for update in resp.json().get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    text = msg.get("text", "").strip()

                    if chat_id not in TELEGRAM_CHAT_IDS:
                        continue

                    if text == "/stop":
                        is_paused = True
                        await send_telegram("⏸ <b>Бот остановлен.</b> Напиши /resume чтобы возобновить.")
                    elif text == "/resume":
                        is_paused = False
                        await send_telegram("▶️ <b>Бот возобновлён!</b>")
                    elif text == "/refresh":
                        asyncio.create_task(run_refresh())
                    elif text == "/mode_all":
                        current_mode = MODE_ALL
                        await send_telegram("✅ Режим: все вакансии")
                    elif text == "/mode_norussia":
                        current_mode = MODE_NO_RUSSIA
                        await send_telegram("✅ Режим: только не из России")
                    elif text == "/mode_remote":
                        current_mode = MODE_REMOTE_ONLY
                        await send_telegram("✅ Режим: только remote/worldwide")
                    elif text == "/mode_asia":
                        current_mode = MODE_ASIA
                        await send_telegram("✅ Режим: Ближний Восток + Азия (ОАЭ, КСА, Катар, Кувейт, Сингапур, Китай, Таиланд, Вьетнам, Малайзия, Филиппины)")
                    elif text == "/mode_cis_eu":
                        current_mode = MODE_CIS_EU
                        await send_telegram("✅ Режим: СНГ + Восточная Европа (Грузия, Армения, Польша, Латвия, Литва, Сербия, Кипр)")
                    elif text == "/status":
                        mode_names = {
                            MODE_ALL: "все вакансии",
                            MODE_NO_RUSSIA: "только не из России",
                            MODE_REMOTE_ONLY: "только remote/worldwide",
                            MODE_ASIA: "Ближний Восток + Азия",
                            MODE_CIS_EU: "СНГ + Восточная Европа",
                        }
                        status = "⏸ На паузе" if is_paused else "▶️ Активен"
                        await send_telegram(
                            f"⚙️ <b>Статус бота</b>\n"
                            f"Состояние: {status}\n"
                            f"Режим: {mode_names.get(current_mode)}\n"
                            f"Проверка: раз в {CHECK_INTERVAL // 3600} ч.\n\n"
                            f"Команды:\n"
                            f"/stop — остановить\n"
                            f"/resume — возобновить\n"
                            f"/mode_all — все вакансии\n"
                            f"/mode_norussia — только не из России\n"
                            f"/mode_remote — только remote/worldwide\n"
                            f"/mode_asia — ОАЭ, КСА, Катар, Сингапур, Азия\n"
                            f"/mode_cis_eu — Грузия, Армения, Польша, Латвия, Литва, Сербия\n"
                            f"/refresh — подборка за 4 дня\n"
                            f"/status — этот экран"
                        )
            except Exception as e:
                print(f"Ошибка polling: {e}")
                await asyncio.sleep(5)

async def main():
    mode_names = {
        MODE_ALL: "все вакансии",
        MODE_NO_RUSSIA: "только не из России",
        MODE_REMOTE_ONLY: "только remote/worldwide",
        MODE_ASIA: "Ближний Восток + Азия",
        MODE_CIS_EU: "СНГ + Восточная Европа",
    }
    await send_telegram(
        f"✅ <b>Construction Job Monitor запущен!</b>\n"
        f"🏗 Ищу: Консультант по строительным проектам\n"
        f"Режим: {mode_names.get(current_mode)}\n"
        f"Проверка раз в {CHECK_INTERVAL // 3600} ч.\n\n"
        f"Команды:\n"
        f"/stop — остановить\n"
        f"/resume — возобновить\n"
        f"/mode_all — все вакансии\n"
        f"/mode_norussia — только не из России\n"
        f"/mode_remote — только remote/worldwide\n"
        f"/mode_asia — ОАЭ, КСА, Катар, Сингапур, Азия\n"
        f"/mode_cis_eu — Грузия, Армения, Польша, Латвия, Литва, Сербия\n"
        f"/refresh — подборка за 4 дня\n"
        f"/status — текущие настройки"
    )

    async def check_loop():
        while True:
            await run_check()
            await asyncio.sleep(CHECK_INTERVAL)

    await asyncio.gather(check_loop(), poll_commands())

if __name__ == "__main__":
    asyncio.run(main())
