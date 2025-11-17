import streamlit as st
import datetime
from datetime import timedelta, date
from collections import namedtuple
from typing import List, Dict, Any
import json
from pathlib import Path

# ============================================================================
# SISTEMA DE TRADUCCIONES (i18n)
# ============================================================================


# --- 1. FUNCIÓN PARA CARGAR EL IDIOMA ---
# 1. Función para cargar TODO el archivo JSON (Optimizada con caché)
@st.cache_data
def load_all_translations():
    """
    Carga el archivo translations.json completo en memoria.
    """
    root_dir = Path(__file__).parent
    file_path = root_dir / "translations.json"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"No se encontró el archivo en: {file_path}")
        return {}
    except json.JSONDecodeError:
        st.error(f"Error de formato en el JSON.")
        return {}


# ==============================================================================
# 2. FUNCIÓN DE TRADUCCIÓN (ACCESO RÁPIDO)
# ==============================================================================
def t(key: str, **kwargs) -> str:
    """
    Busca la traducción usando el diccionario en memoria.
    """
    # 1. Obtenemos el diccionario completo (esto es rapidísimo porque viene de caché)
    all_data = load_all_translations()

    # 2. Obtenemos el idioma actual del estado
    lang = st.session_state.get("language", "es")

    # 3. Navegamos en el diccionario
    #    Primero entramos al idioma, luego buscamos la clave
    lang_data = all_data.get(lang, {})
    translation = lang_data.get(key, key)  # Devuelve la key si no encuentra traducción
    # print(translation)
    # print("++++" * 8)

    # 4. Formateamos si es necesario
    if kwargs:
        return translation.format(**kwargs)

    return translation


def get_day_names() -> List[str]:
    """Retorna los nombres de los días en el idioma actual."""
    return [
        t("monday"),
        t("tuesday"),
        t("wednesday"),
        t("thursday"),
        t("friday"),
        t("saturday"),
        t("sunday"),
    ]


def get_category_options() -> List[str]:
    """Retorna las categorías en el idioma actual."""
    return [t("category_d"), t("category_t"), t("category_a")]


def get_category_code(category_name: str) -> str:
    """Convierte nombre de categoría a código."""
    if category_name in [t("category_d"), "Popular Science", "Divulgación"]:
        return "D"
    elif category_name in [t("category_a"), "Analysis", "Análisis"]:
        return "A"
    else:  # Theory / Teoría
        return "T"


# ============================================================================
# FUNCIONES
# ============================================================================

Book = namedtuple("Book", ["title", "pages", "category"])


def clear_book_list():
    if "book_list" in st.session_state:
        st.session_state.book_list = []


def calculate_reading_time_minutes(
    book: Book, reading_speeds: Dict[str, float]
) -> float:
    minutes_per_page = reading_speeds.get(book.category, 2.0)
    return book.pages * minutes_per_page


def calculate_reading_time_hours(book: Book, reading_speeds: Dict[str, float]) -> float:
    return calculate_reading_time_minutes(book, reading_speeds) / 60


def get_ics_uid(date_obj, title):
    return f"{date_obj.strftime('%Y%m%d')}-{hash(title)}@planlector.streamlit.app"


def format_ics_datetime(dt):
    return dt.strftime("%Y%m%dT%H%M%S")


def escape_ics_text(text):
    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def convert(seconds):
    min, sec = divmod(seconds, 60)
    hour, min = divmod(min, 60)
    return "%02d:%02d" % (min, sec)


def create_valarm_blocks(reminders):
    valarm_blocks = []
    for reminder in reminders:
        minutes = reminder["minutes"]
        description = escape_ics_text(reminder["description"])
        duration = f"-PT{minutes}M"
        valarm_block = [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{description}",
            f"TRIGGER:{duration}",
            "END:VALARM",
        ]
        valarm_blocks.append("\n".join(valarm_block))
    return valarm_blocks


def add_event(
    events_list: List[Dict],
    dt_start: datetime.datetime,
    minutes: float,
    summary: str,
    description: str,
    organizer_email: str,
    organizer_name: str,
    reminders_config: Dict,
    location: str = "",
    status: str = "CONFIRMED",
    is_review: bool = False,
):
    dt_end = dt_start + timedelta(minutes=minutes)
    active_reminders = (
        reminders_config["review"] if is_review else reminders_config["normal"]
    )
    valarm_blocks = create_valarm_blocks(active_reminders)

    events_list.append(
        {
            "uid": get_ics_uid(dt_start, summary),
            "dtstamp": format_ics_datetime(datetime.datetime.now()),
            "dtstart": format_ics_datetime(dt_start),
            "dtend": format_ics_datetime(dt_end),
            "summary": escape_ics_text(summary),
            "description": escape_ics_text(description),
            "location": escape_ics_text(location),
            "organizer_email": organizer_email,
            "organizer_name": escape_ics_text(organizer_name),
            "status": status,
            "valarms": valarm_blocks,
            "sequence": 0,
            "transp": "OPAQUE",
            "class": "PUBLIC",
            "priority": 3 if is_review else 5,
        }
    )


def schedule_book_review(
    events_list: List[Dict],
    review_date: date,
    book_name: str,
    book_hours: float,
    review_time_min: int,
    start_time_review: datetime.time,
    reading_weekdays: List[int],
    organizer_email: str,
    organizer_name: str,
    reminders_config: Dict,
):
    while review_date.weekday() not in reading_weekdays:
        review_date += timedelta(days=1)

    review_start_time = datetime.datetime.combine(review_date, start_time_review)

    add_event(
        events_list,
        review_start_time,
        review_time_min,
        t("review_session", book=book_name),
        t(
            "review_description",
            book=book_name,
            hours=f"{book_hours:.2f}",
            duration=review_time_min,
        ),
        organizer_email,
        organizer_name,
        reminders_config,
        location=t("quiet_space"),
        status="CONFIRMED",
        is_review=True,
    )


def create_reading_plan(
    book_schedule_list: List[Book],
    start_date: date,
    end_date: date,
    daily_time_total_minutes: int,
    review_time_per_book_min: int,
    reading_speeds: Dict[str, float],
    reading_weekdays: List[int],
    start_time_books: datetime.time,
    start_time_review: datetime.time,
    organizer_email: str,
    organizer_name: str,
):
    if not book_schedule_list:
        return (
            [],
            [],
            {"total_events": 0, "books_completed_count": 0, "total_book_hours": 0},
        )

    daily_time_books_min = daily_time_total_minutes

    reminders_config = {
        "normal": [{"minutes": 5, "description": t("reminder_normal", minutes=5)}],
        "review": [{"minutes": 10, "description": t("reminder_review", minutes=10)}],
    }

    events = []
    books_completed = []
    current_book_index = 0
    current_date = start_date

    total_book_hours_calc = sum(
        calculate_reading_time_hours(book, reading_speeds)
        for book in book_schedule_list
    )

    current_book = book_schedule_list[current_book_index]
    current_book_remaining_min = calculate_reading_time_minutes(
        current_book, reading_speeds
    )

    while current_date <= end_date:
        weekday = current_date.weekday()

        if weekday in reading_weekdays:
            session_start_time = datetime.datetime.combine(
                current_date, start_time_books
            )
            remaining_session_time = daily_time_books_min

            while remaining_session_time > 0 and current_book_index < len(
                book_schedule_list
            ):
                current_book = book_schedule_list[current_book_index]
                book_name = current_book.title
                book_hours = calculate_reading_time_hours(current_book, reading_speeds)

                time_to_dedicate = min(
                    remaining_session_time, current_book_remaining_min
                )

                if time_to_dedicate <= 0:
                    break

                add_event(
                    events,
                    session_start_time,
                    time_to_dedicate,
                    t("reading_session", book=book_name),
                    t(
                        "reading_description",
                        book=book_name,
                        remaining=f"{current_book_remaining_min:.0f}",
                        duration=f"{time_to_dedicate:.0f}",
                    ),
                    organizer_email,
                    organizer_name,
                    reminders_config,
                    location=t("study_room"),
                )

                current_book_remaining_min -= time_to_dedicate
                remaining_session_time -= time_to_dedicate
                session_start_time += timedelta(minutes=time_to_dedicate)

                if current_book_remaining_min <= 0.1:
                    books_completed.append(
                        {
                            t("book_title"): book_name,
                            t("total_hours"): round(book_hours, 2),
                            t("end_date"): current_date.strftime("%Y-%m-%d"),
                        }
                    )

                    next_review_date = current_date + timedelta(days=1)
                    schedule_book_review(
                        events,
                        next_review_date,
                        book_name,
                        book_hours,
                        review_time_per_book_min,
                        start_time_review,
                        reading_weekdays,
                        organizer_email,
                        organizer_name,
                        reminders_config,
                    )

                    current_book_index += 1
                    if current_book_index < len(book_schedule_list):
                        next_book = book_schedule_list[current_book_index]
                        current_book_remaining_min = calculate_reading_time_minutes(
                            next_book, reading_speeds
                        )
                    else:
                        if remaining_session_time > 0:
                            add_event(
                                events,
                                session_start_time,
                                remaining_session_time,
                                t("final_review"),
                                t("final_description", count=len(books_completed)),
                                organizer_email,
                                organizer_name,
                                reminders_config,
                                is_review=True,
                            )
                        remaining_session_time = 0
                        break

        current_date += timedelta(days=1)

        if current_book_index >= len(book_schedule_list):
            break

    stats = {
        "total_events": len(events),
        "books_completed_count": len(books_completed),
        "total_book_hours": total_book_hours_calc,
        "total_days": abs(start_date - current_date).days,
    }

    return events, books_completed, stats


def generate_ics_content(
    events, organizer_name, organizer_email, cal_name="Plan de Lectura"
):
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Streamlit Plan Lector//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(cal_name)}",
        "X-WR-TIMEZONE:Europe/Madrid",
    ]

    for event in events:
        event_lines = [
            "BEGIN:VEVENT",
            f"UID:{event['uid']}",
            f"DTSTAMP:{event['dtstamp']}",
            f"DTSTART:{event['dtstart']}",
            f"DTEND:{event['dtend']}",
            f"SUMMARY:{event['summary']}",
            f"DESCRIPTION:{event['description']}",
            f"ORGANIZER;CN={event['organizer_name']}:mailto:{event['organizer_email']}",
            f"LOCATION:{event['location']}",
            f"STATUS:{event['status']}",
            f"SEQUENCE:{event['sequence']}",
            f"TRANSP:{event['transp']}",
            f"CLASS:{event['class']}",
            f"PRIORITY:{event['priority']}",
        ]

        ics_content.extend(event_lines)
        for valarm in event["valarms"]:
            ics_content.append(valarm)
        ics_content.append("END:VEVENT")

    ics_content.append("END:VCALENDAR")
    return "\n".join(ics_content)


# ============================================================================
# INTERFAZ DE STREAMLIT CON TRADUCCIONES
# ============================================================================

# Inicializar idioma en session_state
if "language" not in st.session_state:
    st.session_state.language = "es"

# Configuración de página
st.set_page_config(page_title=t("page_title"), layout="wide")

# SELECTOR DE IDIOMA (en la parte superior)
col_title, col_lang = st.columns([5, 1])

with col_title:
    st.title(t("main_title"))
    st.write(t("main_subtitle"))

with col_lang:
    st.write("")  # Espaciado
    language_option = st.selectbox(
        "🌐",
        options=["🇪🇸 Español", "🇬🇧 English"],
        index=0 if st.session_state.language == "es" else 1,
        label_visibility="collapsed",
    )

    # Actualizar idioma si cambió
    new_lang = "es" if "Español" in language_option else "en"
    if new_lang != st.session_state.language:
        st.session_state.language = new_lang
        st.rerun()

# Inicializar lista de libros
if "book_list" not in st.session_state:
    st.session_state.book_list = []

# --- Barra Lateral ---
st.sidebar.header(t("sidebar_config"))
organizer_name = st.sidebar.text_input(t("your_name"), "Eric")
organizer_email = st.sidebar.text_input(t("your_email"), "ericlucero501@gmail.com")

today = datetime.date.today()
start_date = st.sidebar.date_input(t("start_date"), today + timedelta(days=1))
end_date = st.sidebar.date_input(t("end_date"), today + timedelta(days=121))

if start_date >= end_date:
    st.sidebar.error(t("date_error"))

st.sidebar.header(t("sidebar_times"))
daily_time_total_minutes = st.sidebar.slider(t("daily_minutes"), 60, 480, 120, 5)
review_time_per_book_min = st.sidebar.slider(t("review_minutes"), 30, 120, 60, 5)

day_names = get_day_names()
day_map = {name: i for i, name in enumerate(day_names)}
default_days = [day_names[i] for i in range(6)]  # Lunes a Sábado
selected_day_names = st.sidebar.multiselect(
    t("reading_days"), day_names, default=default_days
)
reading_weekdays = [day_map[name] for name in selected_day_names]

start_time_books = st.sidebar.time_input(t("start_time_books"), datetime.time(10, 0))
start_time_review = st.sidebar.time_input(t("start_time_review"), datetime.time(19, 0))

st.sidebar.header(t("sidebar_speeds"), help=t("speeds_help"))
st.sidebar.caption(t("speeds_caption"))

speed_d = st.sidebar.number_input(
    t("category_d"), min_value=20.0, max_value=360.0, value=120.0, step=1.0
)
st.sidebar.caption(f"⏱️ {convert(speed_d)} {t('minutes_per_page')}")

speed_t = st.sidebar.number_input(
    t("category_t"), min_value=20.0, max_value=360.0, value=145.0, step=1.0
)
st.sidebar.caption(f"⏱️ {convert(speed_t)} {t('minutes_per_page')}")

speed_a = st.sidebar.number_input(
    t("category_a"), min_value=20.0, max_value=360.0, value=180.0, step=1.0
)
st.sidebar.caption(f"⏱️ {convert(speed_a)} {t('minutes_per_page')}")

reading_speeds_dict = {"D": speed_d / 60, "T": speed_t / 60, "A": speed_a / 60}

# --- Sección Principal: Libros ---
st.header(t("books_section"))
st.write(t("books_subtitle"))

with st.form("add_book_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        book_title = st.text_input(t("book_title"))
    with col2:
        book_pages = st.number_input(t("book_pages"), min_value=1, step=10)
    with col3:
        book_category = st.selectbox(t("book_category"), get_category_options())

    submitted = st.form_submit_button(t("add_book"))
    if submitted and book_title and book_pages:
        code = get_category_code(book_category)
        st.session_state.book_list.append(
            {
                t("book_title"): book_title,
                t("book_pages"): book_pages,
                t("book_category"): book_category,
                "Código": code,
            }
        )

if st.session_state.book_list:
    st.subheader(t("books_in_plan"))
    edited_df = st.data_editor(
        st.session_state.book_list,
        num_rows="dynamic",
        key="editor_libros",
        use_container_width=True,
    )

    if st.button(t("clear_list")):
        st.session_state.book_list = []
        st.rerun()
else:
    st.info(t("no_books_yet"))

# --- Generación del Plan ---
st.header(t("generate_section"))

if st.button(t("generate_button")):
    if not st.session_state.book_list:
        st.error(t("error_no_books"))
    elif not reading_weekdays:
        st.error(t("error_no_days"))
    elif start_date >= end_date:
        st.error(t("date_error"))
    else:
        with st.spinner(t("generating")):
            book_tuples_list = [
                Book(
                    title=b[t("book_title")],
                    pages=b[t("book_pages")],
                    category=b["Código"],
                )
                for b in edited_df
            ]

            events, books_completed, stats = create_reading_plan(
                book_schedule_list=book_tuples_list,
                start_date=start_date,
                end_date=end_date,
                daily_time_total_minutes=daily_time_total_minutes,
                review_time_per_book_min=review_time_per_book_min,
                reading_speeds=reading_speeds_dict,
                reading_weekdays=reading_weekdays,
                start_time_books=start_time_books,
                start_time_review=start_time_review,
                organizer_email=organizer_email,
                organizer_name=organizer_name,
            )

            if events:
                cal_name = f"Plan Lectura {start_date.year}"
                ics_data = generate_ics_content(
                    events, organizer_name, organizer_email, cal_name
                )

                st.success(t("success_generated", count=stats["total_events"]))

                col1, col2, col3, col4 = st.columns(4)
                col1.metric(t("total_events"), stats["total_events"])
                col2.metric(t("books_completed"), stats["books_completed_count"])
                col3.metric(t("total_hours"), f"{stats['total_book_hours']:.2f} h")
                col4.metric(t("total_days"), f"{stats['total_days']}")

                if books_completed:
                    st.subheader("Resumen de Libros Completados en el Plan")
                    st.dataframe(books_completed)

                # --- Botón de Descarga ---
                st.download_button(
                    label="📥 Descargar Archivo .ics",
                    data=ics_data,
                    file_name=f"Plan_Lectura_{start_date.strftime('%Y%m%d')}.ics",
                    mime="text/calendar",
                    on_click=clear_book_list,
                )
            else:
                st.warning(
                    "No se generaron eventos. Revisa la configuración o la lista de libros."
                )
