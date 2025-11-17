# 📅 Planificador de Lectura IA & Visor de Contenidos

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green)

Una aplicación web interactiva construida con **Streamlit** que cumple dos funciones principales: generar planes de estudio intensivos exportables a calendario (.ics) y visualizar contenidos literarios almacenados en una base de datos **MongoDB**.

## 🚀 Características Principales

### 1. Generador de Planes de Lectura (.ics)
* **Cálculo Inteligente:** Estima el tiempo de lectura basándose en la categoría del libro (Teoría vs. Divulgación) y la velocidad de lectura del usuario.
* **Agendamiento Automático:** Distribuye las sesiones de lectura en los días seleccionados de la semana.
* **Active Recall:** Programa sesiones de revisión y repaso espaciado automáticamente al terminar cada libro.
* **Exportación Universal:** Genera archivos `.ics` compatibles con Google Calendar, Outlook y Apple Calendar.

### 2. Visor de Contenidos (MongoDB)
* **Conexión a Nube:** Conecta con MongoDB Atlas para recuperar textos y poemas.
* **Filtrado:** Muestra solo documentos marcados como `publicado: true`.
* **Visualización Aleatoria:** Botón para descubrir un poema al azar con estilos CSS personalizados.
* **Caché Eficiente:** Uso de `st.cache_resource` y `st.cache_data` para minimizar latencia y lecturas a la DB.

### 3. Internacionalización (i18n)
* Soporte completo para **Español** e **Inglés**.
* Carga dinámica de archivos JSON para gestionar traducciones.

---

## 🛠️ Instalación y Configuración Local

Sigue estos pasos para ejecutar el proyecto en tu máquina local.

### 1. Clonar el repositorio
```bash
git clone [https://github.com/TU_USUARIO/TU_REPOSITORIO.git](https://github.com/TU_USUARIO/TU_REPOSITORIO.git)
cd TU_REPOSITORIO
```
### 2. Crear un entorno virtual (Recomendado)
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
1. Instalar dependencias
```

```bash
pip install -r requirements.txt
Asegúrate de que tu requirements.txt incluya: streamlit, pymongo, dnspython.
```
### 4. Configurar Secretos (MongoDB)


## 1. Ejecutar la aplicación

```bash
streamlit run app.py
```
### 📂 Estructura del Proyecto
Plaintext
├── app.py                 # Punto de entrada de la aplicación
├── Lectura_plan/
│   └── translations.json  # Archivo JSON con textos EN/ES
├── .streamlit/
│   └── secrets.toml       # Credenciales (NO SUBIR A GITHUB)
├── .gitignore             # Configuración de archivos ignorados
├── requirements.txt       # Librerías de Python
└── README.md              # Documentación
```
🌍 Internacionalización (JSON)
La estructura del archivo translations.json debe ser la siguiente:

```JSON
{
    "es": {
        "main_title": "Generador de Plan de Lectura",
        "welcome_msg": "Bienvenido..."
    },
    "en": {
        "main_title": "Reading Plan Generator",
        "welcome_msg": "Welcome..."
    }
}
```

### ☁️ Despliegue en Streamlit Cloud
Sube tu código a GitHub (asegurándote de que .gitignore excluya secrets.toml).

Inicia sesión en Streamlit Cloud.

Conecta tu repositorio.

En la configuración avanzada ("Advanced Settings"), pega el contenido de tu secrets.toml en el área de Secrets.

### 📝 Licencia
Este proyecto está bajo la Licencia MIT. Siéntete libre de usarlo y modificarlo.

Desarrollado con ❤️ usando Python y Streamlit.