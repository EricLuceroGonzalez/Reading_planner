import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict

st.set_page_config(layout="wide", page_title="Planificador de Lectura Técnica para PhD en IA")

# --- 1. Definición de Tasas y Mapeo ---

# Tasas de lectura conservadoras para entornos académicos:
# 6 pph: Lectura profunda (Pass 3) - Para material técnico (Teoría/T)
# 20 pph: Lectura de contexto (Pass 1/2) - Para material narrativo (Divulgación/D)
TASA_MAPEO: Dict[str, float] = {
    'Teoría/Investigación (T)': 6.0,  
    'Divulgación/Ensayo (D)': 20.0     
}

ESTADOS_PASE: List[str] = ['0 - Pendiente', '1 - Escaneado (Pass 1)', 
                           '2 - Contenido Capturado (Pass 2)', '3 - Implementado (Pass 3)']

# Capacidad cognitiva neta (límite sostenible para material de alta densidad)
HORAS_DIARIAS_NETAS_SOSTENIBLES = 2.0  # Basado en la evidencia 

# --- 2. Inicialización del DataFrame con los 13 Libros ---
# La clave 'Tipo_Material' usa el mapeo T/D.

@st.cache_data
def load_base_data() -> pd.DataFrame:
    """Inicializa el DataFrame con la lista definitiva de 13 libros."""
    
    # Datos de los 13 libros (Título, Páginas, Categoría)
    initial_books = [
        {"Título": "A Brief History of Intelligence", "Páginas_Totales": 112, "Tipo_Material": "Teoría/Investigación (T)"}, # VLT, Académico [7]
        {"Título": "Why Machines Learn (Restante)", "Páginas_Totales": 130, "Tipo_Material": "Teoría/Investigación (T)"}, # VLT
        {"Título": "Programa o serás programado", "Páginas_Totales": 208, "Tipo_Material": "Divulgación/Ensayo (D)"}, # VLD, Ensayo [8]
        {"Título": "Matemáticas revolucionarias", "Páginas_Totales": 206, "Tipo_Material": "Teoría/Investigación (T)"}, # VLT, Filosófico-Crítico [9]
        {"Título": "An Introduction to Metaheuristics for Optimization", "Páginas_Totales": 230, "Tipo_Material": "Teoría/Investigación (T)"}, # VLT, Técnico [10]
        {"Título": "Predicting the Unknown", "Páginas_Totales": 250, "Tipo_Material": "Teoría/Investigación (T)"}, # VLT, Académico
        {"Título": "El andar del borracho", "Páginas_Totales": 272, "Tipo_Material": "Divulgación/Ensayo (D)"}, # VLD, Probabilidad [11]
        {"Título": "El costo de la conexión", "Páginas_Totales": 304, "Tipo_Material": "Divulgación/Ensayo (D)"}, # VLD, Crítica Social [12]
        {"Título": "Redes neuronales recurrentes y transformers", "Páginas_Totales": 320, "Tipo_Material": "Teoría/Investigación (T)"}, # VLT, Core Técnico [13]
        {"Título": "El hombre del futuro", "Páginas_Totales": 328, "Tipo_Material": "Divulgación/Ensayo (D)"}, # VLD, Biografía [14]
        {"Título": "Inteligencia Artificial: Guía para seres pensantes", "Páginas_Totales": 368, "Tipo_Material": "Divulgación/Ensayo (D)"}, # VLD, Guía [15]
        {"Título": "Algorithms to Live By", "Páginas_Totales": 368, "Tipo_Material": "Divulgación/Ensayo (D)"} # VLD, Aplicación [16]
    ]
    
    df = pd.DataFrame(initial_books)
    
    # Inicializar columnas calculadas y de estatus
    df['Tasa_Páginas_Hora'] = 0.0
    df['Horas_Requeridas_Totales'] = 0.0
    df['Días_Proyectados_Fin'] = 0.0
    df['Estatus_Pase'] = '0 - Pendiente'
    
    # Asegurar un ID único
    df['ID'] = range(1, len(df) + 1)
    
    return df.set_index('ID')

# --- 3. Motor de Cálculo Dinámico ---

def calcular_proyecciones(df_input: pd.DataFrame, horas_netas_teoria: float, horas_netas_divulgacion: float) -> pd.DataFrame:
    """Calcula las proyecciones de tiempo basadas en el DataFrame editado y el tiempo diario."""
    df_calc = df_input.copy()
    
    # 1. Asignar Tasa de Páginas/Hora basada en la densidad (Lookup)
    df_calc['Tasa_Páginas_Hora'] = df_calc['Tipo_Material'].apply(lambda x: TASA_MAPEO.get(x, 0))
    
    # 2. Calcular Horas Requeridas Totales
    df_calc['Horas_Requeridas_Totales'] = df_calc['Páginas_Totales'] / df_calc['Tasa_Páginas_Hora']
    
    # 3. Calcular Días Proyectados (diferenciando T/D para la división)
    def calcular_dias(row):
        horas_diarias = horas_netas_teoria if row['Tipo_Material'] == 'Teoría/Investigación (T)' else horas_netas_divulgacion
        if horas_diarias > 0:
            return row['Horas_Requeridas_Totales'] / horas_diarias
        return np.inf # Prevenir división por cero

    df_calc['Días_Proyectados_Fin'] = df_calc.apply(calcular_dias, axis=1)
    
    # Formato para la visualización
    df_calc['Horas_Requeridas_Totales'] = df_calc['Horas_Requeridas_Totales'].round(2)
    df_calc['Días_Proyectados_Fin'] = df_calc['Días_Proyectados_Fin'].round(2)
    
    return df_calc

# --- 4. Configuración y Despliegue de la Interfaz Streamlit ---

# Obtener DataFrame base
df_base = load_base_data()

# --- Parámetros Globales (Sidebar) ---
with st.sidebar:
    st.header("⚙️ Ajuste de Dedicación Diaria")
    st.markdown("Establezca su compromiso de tiempo diario:")
    
    # Se introduce la estrategia del usuario (2h T, 1h D)
    horas_dia_teoria = st.number_input("Horas/día para Teoría/Técnico (VLT)", min_value=0.5, max_value=3.0, value=2.0, step=0.5)
    horas_dia_divulgacion = st.number_input("Horas/día para Divulgación/Ensayo (VLD)", min_value=0.5, max_value=3.0, value=1.0, step=0.5)
    
    # Advertencia basada en el límite de sobrecarga cognitiva para VLT
    if horas_dia_teoria > HORAS_DIARIAS_NETAS_SOSTENIBLES:
        st.error(f"⚠️ ¡Riesgo de Burnout! Sesiones de más de {HORAS_DIARIAS_NETAS_SOSTENIBLES}h en material Técnico (VLT) son contraproducentes para la retención. Se recomienda reducir este tiempo o incluir pausas estructuradas.")
    
    st.markdown("---")
    st.subheader("📊 Cálculo de Carga Total")
    st.info(f"Tiempo Total de Estudio Diario: **{horas_dia_teoria + horas_dia_divulgacion:.1f} horas**")

# --- Despliegue Principal ---
st.title("📚 Planificador de Lectura PhD en IA (90 Días)")
st.caption("Herramienta para optimizar la asimilación de textos de alta densidad (VLT: 6 pph | VLD: 20 pph).")

# 5. Configuración del Editor de Datos
column_config_dict = {
    "Título": st.column_config.TextColumn("Título/Ítem", required=True, width="large"),
    "Páginas_Totales": st.column_config.NumberColumn("Páginas Totales", min_value=1, format="%d"),
    
    "Tipo_Material": st.column_config.SelectboxColumn(
        "Clasificación (T/D)", options=list(TASA_MAPEO.keys()), required=True
    ),
    "Estatus_Pase": st.column_config.SelectboxColumn(
        "Estatus (3-Pass Method)", options=ESTADOS_PASE, required=True, help="Seguimiento de la metodología de lectura de artículos científicos."
    ),
    "Tasa_Páginas_Hora": st.column_config.NumberColumn("Páginas/Hora", disabled=True, format="%.1f"),
    "Horas_Requeridas_Totales": st.column_config.NumberColumn("Horas Totales", disabled=True, format="%.2f"),
    "Días_Proyectados_Fin": st.column_config.NumberColumn("Días Proyectados", disabled=True, help="Días de lectura efectiva a su ritmo diario.", format="%.2f")
}

# El data_editor para la entrada y edición del usuario
edited_df = st.data_editor(
    df_base,
    column_config=column_config_dict,
    num_rows="dynamic",
    use_container_width=True
)

# Recalcular si hay cambios
if edited_df is not None:
    final_df = calcular_proyecciones(edited_df, horas_dia_teoria, horas_dia_divulgacion)
    
    # Cálculo de Totales
    total_horas_proyecto = final_df['Horas_Requeridas_Totales'].sum()
    
    # Calcular días totales para el proyecto (usando el cuello de botella T/D)
    horas_T = final_df[final_df['Tipo_Material'] == 'Teoría/Investigación (T)']['Horas_Requeridas_Totales'].sum()
    horas_D = final_df[final_df['Tipo_Material'] == 'Divulgación/Ensayo (D)']['Horas_Requeridas_Totales'].sum()
    
    dias_T = horas_T / horas_dia_teoria if horas_dia_teoria > 0 else 0
    dias_D = horas_D / horas_dia_divulgacion if horas_dia_divulgacion > 0 else 0
    
    dias_cuello_botella = max(dias_T, dias_D)
    
    # Mostrar tabla actualizada
    st.subheader("📊 Tabla de Proyecciones Actualizadas")
    st.dataframe(
        final_df.reset_index(),
        column_config=column_config_dict,
        use_container_width=True,
        hide_index=True
    )
    
    # Resumen de proyección
    st.markdown("---")
    st.subheader("📈 Resumen de Proyección (Análisis de Cuello de Botella)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Horas Totales Requeridas", f"{total_horas_proyecto:.1f}h")
    
    with col2:
        st.metric("Días Efectivos Necesarios", f"{dias_cuello_botella:.0f} días")
    
    with col3:
        margen = 90 - dias_cuello_botella
        st.metric("Margen de Tiempo (90 días)", f"{margen:.0f} días", 
                 delta=f"{(margen/90)*100:.1f}% buffer")
    
    # Desglose detallado
    with st.expander("📋 Ver Análisis Detallado"):
        st.markdown(f"""
        ### Desglose por Tipo de Material
        
        **📖 Bloque Teoría/Técnico (VLT):**
        - Horas requeridas: **{horas_T:.2f} horas**
        - Ritmo diario: **{horas_dia_teoria:.1f} horas/día**
        - Días necesarios: **{dias_T:.2f} días**
        - Tasa de lectura: **6 páginas/hora**
        
        **📚 Bloque Divulgación/Ensayo (VLD):**
        - Horas requeridas: **{horas_D:.2f} horas**
        - Ritmo diario: **{horas_dia_divulgacion:.1f} horas/día**
        - Días necesarios: **{dias_D:.2f} días**
        - Tasa de lectura: **20 páginas/hora**
        
        ### Conclusión
        
        **Duración del Proyecto:** El plan completo durará aproximadamente **{dias_cuello_botella:.0f} días efectivos**, 
        determinado por el cuello de botella en el bloque **{'Teoría/Técnico (VLT)' if dias_T > dias_D else 'Divulgación/Ensayo (VLD)'}**.
        
        {'✅ **Viable:** Este cronograma es factible dentro del plazo de 90 días, con un margen de ' + f'{margen:.0f} días para revisión y contingencias.' if margen > 0 else '⚠️ **Ajuste Requerido:** El plan excede los 90 días. Considere aumentar el tiempo diario o reducir el número de libros.'}
        """)
    
    # Visualización de distribución
    st.markdown("---")
    st.subheader("📊 Distribución de Carga de Trabajo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de barras por tipo
        tipo_summary = final_df.groupby('Tipo_Material')['Horas_Requeridas_Totales'].sum().reset_index()
        tipo_summary.columns = ['Tipo', 'Horas']
        st.bar_chart(tipo_summary.set_index('Tipo'))
    
    with col2:
        # Estadísticas adicionales
        libros_T = len(final_df[final_df['Tipo_Material'] == 'Teoría/Investigación (T)'])
        libros_D = len(final_df[final_df['Tipo_Material'] == 'Divulgación/Ensayo (D)'])
        
        st.markdown(f"""
        **Estadísticas:**
        - Total de libros: **{len(final_df)}**
        - Libros Técnicos (T): **{libros_T}**
        - Libros Divulgación (D): **{libros_D}**
        - Promedio horas/libro: **{total_horas_proyecto/len(final_df):.1f}h**
        """)
    
    # Advertencias y recomendaciones
    st.markdown("---")
    st.subheader("💡 Recomendaciones")
    
    if horas_dia_teoria > HORAS_DIARIAS_NETAS_SOSTENIBLES:
        st.warning(f"""
        ⚠️ **Alerta de Sobrecarga Cognitiva:** 
        Estás dedicando {horas_dia_teoria:.1f}h diarias a material técnico, 
        superando el límite sostenible de {HORAS_DIARIAS_NETAS_SOSTENIBLES}h. 
        Esto puede afectar negativamente la retención y comprensión.
        
        **Sugerencias:**
        - Incorpora técnicas de spaced repetition
        - Añade pausas de 10-15 min cada hora
        - Considera reducir a {HORAS_DIARIAS_NETAS_SOSTENIBLES}h y extender el plazo
        """)
    
    if margen < 10:
        st.info("""
        ℹ️ **Margen Ajustado:** Tienes poco margen para imprevistos. 
        Considera agregar días buffer o ser flexible con las fechas límite.
        """)
    
    if dias_cuello_botella > 90:
        st.error(f"""
        ❌ **Plan No Viable:** Necesitas {dias_cuello_botella - 90:.0f} días adicionales.
        
        **Opciones:**
        1. Aumentar tiempo diario de lectura
        2. Reducir número de libros
        3. Extender el plazo total
        """)
    else:
        st.success(f"""
        ✅ **Plan Viable:** Completarás tu lectura en {dias_cuello_botella:.0f} días, 
        con {margen:.0f} días de margen para revisión profunda y consolidación.
        """)