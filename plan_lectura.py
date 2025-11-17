import streamlit as st
import datetime
from datetime import timedelta, date
from collections import namedtuple
from typing import List, Dict, Any

# --- DEFINICIÓN DEL TIPO DE DATO LIBRO ---
Book = namedtuple("Book", ["title", "pages", "category"])


# ============================================================================
# FUNCIONES DE LÓGICA (Refactorizadas del script original)
# ============================================================================
def clear_book_list():
    """
    Limpia la lista de libros en el session_state.
    """
    if "book_list" in st.session_state:
        st.session_state.book_list = []


# --- Funciones de cálculo de tiempo ---


def calculate_reading_time_minutes(
    book: Book, reading_speeds: Dict[str, float]
) -> float:
    """Calcula los minutos totales para leer un libro."""
    minutes_per_page = reading_speeds.get(book.category, 2.0)  # Default 2.0
    return book.pages * minutes_per_page


def calculate_reading_time_hours(book: Book, reading_speeds: Dict[str, float]) -> float:
    """Calcula las horas totales para leer un libro."""
    return calculate_reading_time_minutes(book, reading_speeds) / 60


# --- Funciones de formato ICS ---


def get_ics_uid(date_obj, title):
    """Genera un ID único para el evento ICS."""
    return f"{date_obj.strftime('%Y%m%d')}-{hash(title)}@planlector.streamlit.app"


def format_ics_datetime(dt):
    """Formatea datetime a string ICS (DTSTART/DTEND)."""
    return dt.strftime("%Y%m%dT%H%M%S")


def escape_ics_text(text):
    """Escapa caracteres especiales según RFC 5545."""
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


# --- Funciones de creación de eventos ---


def create_valarm_blocks(reminders):
    """Crea bloques VALARM para recordatorios."""
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
    """Añade un evento con recordatorios al array de eventos."""
    dt_end = dt_start + timedelta(minutes=minutes)

    # Crear bloques de alarmas
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
    """Programa una sesión de revisión para un libro completado."""
    # Buscar el siguiente día laboral disponible
    while review_date.weekday() not in reading_weekdays:
        review_date += timedelta(days=1)

    review_start_time = datetime.datetime.combine(review_date, start_time_review)

    add_event(
        events_list,
        review_start_time,
        review_time_min,
        f"🔄 REVISIÓN COMPLETA: {book_name}",
        f"Sesión de consolidación y Active Recall\n\n"
        f"📚 Libro completado: {book_name}\n"
        f"⏱️ Tiempo total invertido: {book_hours:.2f} horas\n"
        f"🎯 Duración de revisión: {review_time_min} minutos\n\n"
        f"OBJETIVOS DE LA SESIÓN:\n"
        f"✓ Active Recall completo del libro\n"
        f"✓ Revisar todas las notas y anotaciones\n"
        f"✓ Crear/actualizar mapa conceptual\n"
        f"✓ Conectar con otros libros leídos\n"
        f"✓ Elaborar resumen ejecutivo",
        organizer_email,
        organizer_name,
        reminders_config,
        location="Espacio de estudio tranquilo",
        status="CONFIRMED",
        is_review=True,
    )


# ============================================================================
# LÓGICA PRINCIPAL DE GENERACIÓN DEL PLAN
# ============================================================================


def create_reading_plan(
    book_schedule_list: List[Book],
    start_date: date,
    end_date: date,
    daily_time_total_minutes: int,
    review_time_per_book_min: int,
    reading_speeds: Dict[str, float],
    reading_weekdays: List[int],  # Lista de enteros 0=Lunes, 6=Domingo
    start_time_books: datetime.time,
    # start_time_articles: datetime.time,
    start_time_review: datetime.time,
    organizer_email: str,
    organizer_name: str,
):
    """
    Genera la lista completa de eventos del calendario.
    """

    if not book_schedule_list:
        return (
            [],
            [],
            {"total_events": 0, "books_completed_count": 0, "total_book_hours": 0},
        )

    # --- Configuración de tiempo ---
    daily_time_books_min = daily_time_total_minutes
    # daily_time_articles_min = daily_time_total_minutes - daily_time_books_min

    # --- Configuración de recordatorios (hardcoded como en el script original) ---
    reminders_config = {
        "normal": [
            {"minutes": 5, "description": "5 minutos antes - Prepara materiales"}
        ],
        "review": [
            {"minutes": 10, "description": "10 minutos antes - Sesión de consolidación"}
        ],
    }

    # --- Inicialización de variables ---
    events = []
    books_completed = []
    current_book_index = 0
    current_date = start_date

    total_book_hours_calc = sum(
        calculate_reading_time_hours(book, reading_speeds)
        for book in book_schedule_list
    )

    # Asegurarnos de que el primer libro está cargado
    current_book = book_schedule_list[current_book_index]
    current_book_remaining_min = calculate_reading_time_minutes(
        current_book, reading_speeds
    )

    # --- Bucle principal ---
    while current_date <= end_date:
        weekday = current_date.weekday()

        # Solo procesar si es un día de lectura seleccionado
        if weekday in reading_weekdays:

            # 1. BLOQUE DE LECTURA DE LIBROS
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
                    break  # Evitar eventos de 0 minutos si el libro ya se acabó

                add_event(
                    events,
                    session_start_time,
                    time_to_dedicate,
                    f"📚 LECTURA: {book_name}",
                    f"Sesión de lectura profunda\n\n"
                    f"📖 Libro: {book_name}\n"
                    f"⏳ Tiempo restante del libro: {current_book_remaining_min:.0f} min\n"
                    f"⏱️ Duración sesión: {time_to_dedicate:.0f} min",
                    organizer_email,
                    organizer_name,
                    reminders_config,
                    location="Sala de estudio",
                )

                current_book_remaining_min -= time_to_dedicate
                remaining_session_time -= time_to_dedicate
                session_start_time += timedelta(minutes=time_to_dedicate)

                # --- LÓGICA DE FINALIZACIÓN DE LIBRO ---
                if current_book_remaining_min <= 0.1:  # Usar un umbral pequeño
                    books_completed.append(
                        {
                            "Libro": book_name,
                            "Horas": round(book_hours, 2),
                            "Fecha de finalización": current_date.strftime("%Y-%m-%d"),
                        }
                    )

                    # Programar revisión
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

                    # Avanzar al siguiente libro
                    current_book_index += 1
                    if current_book_index < len(book_schedule_list):
                        next_book = book_schedule_list[current_book_index]
                        current_book_remaining_min = calculate_reading_time_minutes(
                            next_book, reading_speeds
                        )
                    else:
                        # Todos los libros completados
                        if remaining_session_time > 0:
                            add_event(
                                events,
                                session_start_time,
                                remaining_session_time,
                                "🎓 REVISIÓN GENERAL FINAL",
                                f"Sesión de integración. ¡Todos los libros completados!\n"
                                f"Libros completados: {len(books_completed)}",
                                organizer_email,
                                organizer_name,
                                reminders_config,
                                is_review=True,
                            )
                        remaining_session_time = 0
                        break  # Salir del while de sesión

            # # 2. BLOQUE DE LECTURA DE ARTÍCULOS
            # if daily_time_articles_min > 0:
            #     article_start_time = datetime.datetime.combine(
            #         current_date, start_time_articles
            #     )
            #     add_event(
            #         events,
            #         article_start_time,
            #         daily_time_articles_min,
            #         "📄 ARTÍCULOS: Three-Pass Reading",
            #         f"Lectura crítica de papers científicos\n\n"
            #         f"⏱️ Duración: {daily_time_articles_min} min\n"
            #         f"📖 Método: Three-Pass Reading (Keshav, 2007)",
            #         organizer_email,
            #         organizer_name,
            #         reminders_config,
            #         location="Despacho / Sala de lectura",
            #     )

        # Avanzar al siguiente día
        current_date += timedelta(days=1)

        # Detener si hemos terminado todos los libros (opcional, pero bueno)
        if current_book_index >= len(book_schedule_list):
            st.success(
                f"¡Todos los libros se completarán el {current_date.strftime('%Y-%m-%d')}!"
            )
            break  # Salir del bucle de días principal

    stats = {
        "total_events": len(events),
        "books_completed_count": len(books_completed),
        "total_book_hours": total_book_hours_calc,
        "total_days": abs(start_date - current_date).days,
    }

    return events, books_completed, stats


# --- Función de generación de archivo ICS ---


def generate_ics_content(
    events, organizer_name, organizer_email, cal_name="Plan de Lectura"
):
    """Genera el contenido de string del archivo ICS."""
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Streamlit Plan Lector//ES",
        "CALSCALE:GREGREGORIAN",
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
# INTERFAZ DE STREAMLIT
# ============================================================================

st.set_page_config(page_title="Generador de Plan de Lectura", layout="wide")
st.title("📅 Generador de Plan de Lectura (.ics)")
st.write(
    "Esta app crea un plan de lectura detallado en 5 pasos, y lo exporta como un archivo `.ics` para tu calendario."
)

# --- Inicializar Session State para la lista de libros ---
if "book_list" not in st.session_state:
    st.session_state.book_list = []


# --- Barra Lateral de Configuración ---
st.sidebar.header("⚙️ 1. Configuración General")
organizer_name = st.sidebar.text_input("Tu Nombre", "Eric")
organizer_email = st.sidebar.text_input("Tu Email", "ericlucero501@gmail.com")

today = datetime.date.today()
start_date = st.sidebar.date_input("Fecha de Inicio", today + timedelta(days=1))
end_date = st.sidebar.date_input("Fecha de Fin", today + timedelta(days=121))

if start_date >= end_date:
    st.sidebar.error("La fecha de fin debe ser posterior a la fecha de inicio.")

st.sidebar.header("⏱️ 2. Configuración de Tiempos")
daily_time_total_minutes = st.sidebar.slider(
    "Minutos totales de lectura por día", 60, 480, 120, 5
)

review_time_per_book_min = st.sidebar.slider(
    "Minutos de revisión (al finalizar)", 30, 120, 60, 5
)

day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
day_map = {name: i for i, name in enumerate(day_names)}
selected_day_names = st.sidebar.multiselect(
    "Días de lectura por semana",
    day_names,
    default=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
)
reading_weekdays = [day_map[name] for name in selected_day_names]  # Convertir a 0-6

start_time_books = st.sidebar.time_input(
    "Hora de inicio (Lectura)", datetime.time(10, 0)
)
# start_time_articles = st.sidebar.time_input(
#     "Hora de inicio (Artículos)", datetime.time(12, 30)
# )
start_time_review = st.sidebar.time_input(
    "Hora de inicio (Revisión)", datetime.time(19, 0)
)

st.sidebar.header(
    "⚡ 3. Velocidades de Lectura",
    help="Se recomienda probar con una breve lectura, y cronometrar el tiempo por página para ajustar estas velocidades.",
)
st.sidebar.caption("(Elige el tiempo de lectura en segundos por página)")
speed_d = st.sidebar.number_input(
    "Divulgación (D)", min_value=20.0, max_value=360.0, value=120.0, step=1.0
)
st.sidebar.badge(f"{convert(speed_d)} minutos por pagina")
st.sidebar.divider()

speed_t = st.sidebar.number_input(
    "Teoría (T)", min_value=20.0, max_value=360.0, value=145.0, step=1.0
)
st.sidebar.badge(
    f"{convert(speed_t)} minutos por pagina", icon=None, color="blue", width="content"
)
st.sidebar.divider()

speed_a = st.sidebar.number_input(
    "Análisis (A)", min_value=20.0, max_value=360.0, value=180.0, step=1.0
)
st.sidebar.badge(f"{convert(speed_a)} minutos por pagina")

reading_speeds_dict = {"D": speed_d / 60, "T": speed_t / 60, "A": speed_a / 60}


# --- Página Principal: Lista de Libros y Generación ---

st.header("📚 4. Lista de Libros")
st.write("Añade los libros que quieres incluir en tu plan de lectura.")

# --- Formulario para añadir libros ---
with st.form("add_book_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        book_title = st.text_input("Título del Libro")
    with col2:
        book_pages = st.number_input("Nº de Páginas", min_value=1, step=10)
    with col3:
        book_category = st.selectbox("Categoría", ["Divulgación", "Teoría", "Análisis"])

    submitted = st.form_submit_button("Añadir Libro a la Lista")
    if submitted and book_title and book_pages:
        if book_category == "Análisis":
            st.session_state.book_list.append(
                {
                    "Título": book_title,
                    "Páginas": book_pages,
                    "Categoría": book_category,
                    "Código": "A",
                }
            )
        elif book_category == "Divulgación":
            st.session_state.book_list.append(
                {
                    "Título": book_title,
                    "Páginas": book_pages,
                    "Categoría": book_category,
                    "Código": "D",
                }
            )
        else:  # Teoría
            st.session_state.book_list.append(
                {
                    "Título": book_title,
                    "Páginas": book_pages,
                    "Categoría": book_category,
                    "Código": "T",
                }
            )

# --- Mostrar lista de libros actual ---
if st.session_state.book_list:
    st.subheader("Libros en el Plan:")
    # ✅ EDITABLE
    edited_df = st.data_editor(
        st.session_state.book_list,
        num_rows="dynamic",  # Permite agregar/eliminar
        column_config={
            "Libro": st.column_config.TextColumn("Título", required=True),
            "Páginas": st.column_config.NumberColumn(
                "Páginas", min_value=1, max_value=1000
            ),
            "Tipo": st.column_config.SelectboxColumn("Categoría", options=["T", "D"]),
        },
        key="editor_libros",
    )
    # st.dataframe(st.session_state.book_list)

    if st.button("Limpiar Lista de Libros"):
        st.session_state.book_list = []
        st.rerun()
else:
    st.info("Aún no has añadido ningún libro.")
    # st.badge("Success", icon="⚠️", color="orange")


# --- Botón de Generación ---
st.header("🚀 5. Generar Plan")

if st.button("Generar Plan de Lectura"):
    # --- Validaciones ---
    if not st.session_state.book_list:
        st.error("¡Añade al menos un libro a la lista!")
    elif not reading_weekdays:
        st.error("¡Selecciona al menos un día de lectura a la semana!")
    elif start_date >= end_date:
        st.error("La fecha de fin debe ser posterior a la fecha de inicio.")
    else:
        with st.spinner(
            "Calculando tu plan de lectura... Esto puede tardar un momento."
        ):

            # --- Preparar datos ---
            book_tuples_list = [
                Book(title=b["Título"], pages=b["Páginas"], category=b["Código"])
                for b in edited_df
            ]

            # --- Ejecutar lógica ---
            events, books_completed, stats = create_reading_plan(
                book_schedule_list=book_tuples_list,
                start_date=start_date,
                end_date=end_date,
                daily_time_total_minutes=daily_time_total_minutes,
                review_time_per_book_min=review_time_per_book_min,
                reading_speeds=reading_speeds_dict,
                reading_weekdays=reading_weekdays,
                start_time_books=start_time_books,
                # start_time_articles=start_time_articles,
                start_time_review=start_time_review,
                organizer_email=organizer_email,
                organizer_name=organizer_name,
            )

            # --- Generar contenido ICS ---
            if events:
                cal_name = f"Plan Lectura {start_date.year}"
                ics_data = generate_ics_content(
                    events, organizer_name, organizer_email, cal_name
                )

                st.success(
                    f"¡Plan generado con éxito! Se crearon {stats['total_events']} eventos en el calendario."
                )

                # --- Mostrar estadísticas ---
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Eventos Totales", stats["total_events"])
                col2.metric("Libros Completados", stats["books_completed_count"])
                col3.metric(
                    "Horas Totales (Libros)", f"{stats['total_book_hours']:.2f} h"
                )
                col4.metric("Días Totales", f"{stats['total_days']} días")
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
