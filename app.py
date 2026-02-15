import streamlit as st
import pandas as pd
from PIL import Image

st.set_page_config(
    page_title="AmazingViewDemo",
    page_icon="logo.png",
    layout="wide"
)

# ===== SIDEBAR =====
with st.sidebar:
    logo = Image.open("logo.png")
    st.image(logo, use_container_width=True)

    st.markdown("### AmazingViewDemo")

    menu = st.radio(
        "Menú",
        [
            "Check-outs por día",
            "Lista de huéspedes por departamento",
            "Entradas y salidas por día"
        ]
    )

# ===== TÍTULO PRINCIPAL =====
st.title("Gestión de Reservas Airbnb")

# =========================
# Subir archivos
# =========================
archivos = st.file_uploader("📂 Sube tus archivos CSV", type="csv", accept_multiple_files=True)

if not archivos:
    st.info("Sube al menos un archivo CSV para comenzar")
    st.stop()

frames = []
for archivo in archivos:
    df_temp = pd.read_csv(archivo)
    df_temp["__archivo__"] = archivo.name
    frames.append(df_temp)

df = pd.concat(frames, ignore_index=True)

# =========================
# CSV MAESTRO DEL FORM (una sola vez)
# =========================
form_master_file = st.file_uploader(
    "📄 Sube el CSV maestro de Check-in / Check-out (Forms)",
    type="csv",
    key="form_master"
)

if form_master_file:
    st.session_state.df_form = pd.read_csv(form_master_file)

# =========================
# Filtrar canceladas
# =========================
if "Estado" in df.columns:
    df = df[df["Estado"].astype(str).str.strip().str.lower() != "cancelada por el huésped"]
    st.success("Reservas canceladas filtradas")

# =========================
# Procesar fechas
# =========================
df["Hasta"] = pd.to_datetime(df["Hasta"], dayfirst=True, errors="coerce")
df["Hasta_solo_fecha"] = df["Hasta"].dt.date

# =========================
# Códigos
# =========================
codigo_map = {
    "Amazing Apart + Pool + Gym- Miraflores & Surquillo": "203 (Surquillo)",
    "Amazing & Luxury Apart - San Isidro & Magdalena": "307 (Magdalena)",
    "Amazing Apart + Pool + Gym - Barranco & Miraflores": "508",
    "Amazing & Luxury Apart - Jesus Maria": "2105 (Jesus Maria)",
    "Amazing View + Pool + Gym - Barranco & Miraflores": "1103",
    "Amazing View 2 + Pool + Gym- Barranco & Miraflores": "1003",
    "Amazing View 3 + Pool + Gym- Barranco & Miraflores": "1415",
    "Amazing View 4 + Pool + Gym- Barranco & Miraflores": "1008",
    "Amazing View 5 + Pool + Gym- Barranco & Miraflores": "1716",
    "Amazing View 6 + Pool + Gym- Barranco & Miraflores": "1010",
    "Amazing View 7 + Pool + Gym- Barranco & Miraflores": "810",
    "Casa increible con AC + Jardín + Centrico": "Casa de Tarapoto",
    "Apartamento increíble y lujoso ll - Jesús María": "1103 Botanika (Jesús María)"
}

df["Codigo_corto"] = df["Anuncio"].map(codigo_map).fillna("SIN CODIGO")

# =========================
# SECCIONES POR MENÚ
# =========================

if menu == "Check-outs por día":

    import datetime

    # Estado inicial
    if "mostrar_checkouts" not in st.session_state:
        st.session_state.mostrar_checkouts = False

    if "fecha_checkout" not in st.session_state:
        st.session_state.fecha_checkout = datetime.date.today()

    st.header("Gestión de reservas por Airbnb")

    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        if st.button("⬅️"):
            st.session_state.fecha_checkout -= datetime.timedelta(days=1)
            st.session_state.mostrar_checkouts = True   # automático

    with col3:
        if st.button("➡️"):
            st.session_state.fecha_checkout += datetime.timedelta(days=1)
            st.session_state.mostrar_checkouts = True   # automático

    with col2:
        fecha = st.date_input(
            "Selecciona fecha",
            value=st.session_state.fecha_checkout
        )

    st.session_state.fecha_checkout = fecha

    # Botón inicial
    if st.button("Ver check-outs"):
        st.session_state.mostrar_checkouts = True

    # Mostrar SOLO cuando corresponda
    if st.session_state.mostrar_checkouts:

        resultado = df[df["Hasta_solo_fecha"] == fecha][
            ["Codigo_corto", "Anuncio", "Nombre del huésped", "Hasta"]
        ].sort_values("Codigo_corto")

        st.subheader(f"Check-outs para {fecha.strftime('%d/%m/%Y')}")

        if resultado.empty:
            st.warning("No hay check-outs para este día")
        else:
            st.dataframe(resultado, use_container_width=True)

elif menu == "Lista de huéspedes por departamento":
    st.header("Lista de reservas por departamento")

    col_inicio = 'Fecha de inicio'
    col_adultos = 'Número de adultos'
    col_ninos = 'Número de niños'
    col_bebes = 'Número de bebés'

    df[col_inicio] = pd.to_datetime(df[col_inicio], dayfirst=True, errors='coerce')

    df['Total_huespedes'] = (
        df[col_adultos].fillna(0)
        + df[col_ninos].fillna(0)
        + df[col_bebes].fillna(0)
    ).astype(int)

    c1, c2 = st.columns(2)
    with c1:
        fecha_inicio = st.date_input("Desde", key="desde")
    with c2:
        fecha_fin = st.date_input("Hasta", key="hasta")

    if st.button("Generar lista por departamento"):

        fi = pd.to_datetime(fecha_inicio)
        ff = pd.to_datetime(fecha_fin)

        data = df[(df[col_inicio] <= ff) & (df['Hasta'] >= fi)].copy()
        data = data.sort_values(['Codigo_corto', col_inicio])

        if data.empty:
            st.warning("No hay reservas en ese rango")
        else:
            for codigo, grupo in data.groupby('Codigo_corto'):
                st.markdown(f"### 🏠 {codigo}")

                for _, r in grupo.iterrows():
                    desde = r[col_inicio].strftime('%d/%m')
                    hasta = r['Hasta'].strftime('%d/%m')
                    nombre = str(r['Nombre del huésped']).lower()
                    total = int(r['Total_huespedes'])
                    extra = f" +{total-1}" if total > 1 else ""

                    st.write(f"{desde}-{hasta}: {nombre}{extra}")


elif menu == "Entradas y salidas por día":

    import datetime
    from datetime import timedelta

    st.header("Entradas y salidas por día")

    if "df_form" not in st.session_state:
        st.warning("⚠️ Sube primero el CSV maestro del formulario")
        st.stop()

    df_form = st.session_state.df_form.copy()
    df_airbnb = df.copy()

    # ==========================================
    # 1. ESTADO DE SESIÓN (Para las flechas)
    # ==========================================
    if "fecha_cursor" not in st.session_state:
        st.session_state.fecha_cursor = datetime.date.today()
    
    if "mostrar_resultados" not in st.session_state:
        st.session_state.mostrar_resultados = False

    # ==========================================
    # 2. FUNCIONES DE LIMPIEZA
    # ==========================================
    def normalizar_texto(texto):
        if pd.isna(texto): return ""
        import unicodedata, re
        texto = str(texto).lower()
        texto = unicodedata.normalize("NFD", texto)
        texto = texto.encode("ascii", "ignore").decode("utf-8")
        texto = texto.replace("-", " ") 
        texto = re.sub(r"[^a-z0-9\s]", "", texto)
        texto = re.sub(r"\s+", " ", texto).strip()
        return texto

    def limpiar_dni(dni):
        if pd.isna(dni): return ""
        dni_str = str(dni).strip()
        if dni_str.endswith(".0"):
            dni_str = dni_str[:-2]
        return dni_str
    
    def formatear_nombre_mostrar(nombre_completo):
        if pd.isna(nombre_completo): return "Huésped"
        tokens = str(nombre_completo).strip().split()
        if len(tokens) >= 2:
            return f"{tokens[0].title()} {tokens[1].title()}"
        elif tokens:
            return tokens[0].title()
        return "Huésped"

    def formatear_hora(hora_raw):
        if pd.isna(hora_raw): return "??"
        try:
            return hora_raw.strftime("%I:%M %p").lower().replace(":00", "")
        except:
            s = str(hora_raw).lower()
            return s.replace(":00", "").replace(".", "")

    # ==========================================
    # 3. PREPARACIÓN DE DATOS
    # ==========================================
    col_llegada_form = "Fecha de Llegada | Arrival Date"
    col_salida_form = "Fecha de Salida | Departure Date"
    col_dni_airbnb = "N° Documento de Identidad o Pasaporte"
    
    df_form["fecha_in"] = pd.to_datetime(df_form[col_llegada_form], dayfirst=True, errors="coerce").dt.date
    df_form["fecha_out"] = pd.to_datetime(df_form[col_salida_form], dayfirst=True, errors="coerce").dt.date
    
    df_airbnb["fecha_in"] = pd.to_datetime(df_airbnb["Fecha de inicio"], dayfirst=True, errors="coerce").dt.date
    df_airbnb["fecha_out"] = pd.to_datetime(df_airbnb["Hasta"], dayfirst=True, errors="coerce").dt.date

    df_form["dni_clean"] = df_form["N° Documento de Identidad o Pasaporte | N° ID or Passport"].apply(limpiar_dni)
    df_form["nombre_norm"] = df_form["Nombre completo | Full Name"].apply(normalizar_texto)
    
    if col_dni_airbnb in df_airbnb.columns:
        df_airbnb["dni_clean"] = df_airbnb[col_dni_airbnb].apply(limpiar_dni)
    else:
        df_airbnb["dni_clean"] = ""

    df_airbnb["nombre_norm"] = df_airbnb["Nombre del huésped"].apply(normalizar_texto)

    # ==========================================
    # 4. CONTROLES DE FECHA (FLECHAS)
    # ==========================================
    
    col1, col2, col3, col4 = st.columns([1, 2, 1, 2])

    with col1:
        # Solo mostrar flechas si ya activamos la vista
        if st.session_state.mostrar_resultados:
            if st.button("⬅️ Día anterior"):
                st.session_state.fecha_cursor -= timedelta(days=1)

    with col2:
        # El date_input actualiza el estado
        nueva_fecha = st.date_input(
            "Fecha seleccionada", 
            value=st.session_state.fecha_cursor,
            label_visibility="collapsed"
        )
        # Sincronizamos si el usuario cambia el calendario manual
        if nueva_fecha != st.session_state.fecha_cursor:
            st.session_state.fecha_cursor = nueva_fecha

    with col3:
        if st.session_state.mostrar_resultados:
            if st.button("Día siguiente ➡️"):
                st.session_state.fecha_cursor += timedelta(days=1)
    
    with col4:
        # Botón inicial para activar
        if not st.session_state.mostrar_resultados:
            if st.button("🔍 Mostrar resultados", type="primary"):
                st.session_state.mostrar_resultados = True
                st.rerun()

    # ==========================================
    # 5. LÓGICA DE BÚSQUEDA CORREGIDA (Huéspedes Repetidos)
    # ==========================================
    
    def buscar_match_inteligente(row_airbnb, df_todo_form, tipo_fecha_col, fecha_objetivo):
        """
        1. Busca a TODOS los posibles candidatos (por DNI o Nombre).
        2. De esos candidatos, busca SI ALGUNO coincide con la fecha exacta.
        3. Si no, devuelve el más reciente con error de fecha.
        """
        match_candidates = pd.DataFrame()
        dni_ab = row_airbnb["dni_clean"]
        
        # A) Buscar candidatos por DNI
        if isinstance(dni_ab, str) and len(dni_ab) > 4:
            match_candidates = df_todo_form[df_todo_form["dni_clean"] == dni_ab]
        
        # B) Buscar candidatos por Nombre (si DNI falla)
        if match_candidates.empty:
            nombre_ab_tokens = set(row_airbnb["nombre_norm"].split())
            
            def calcular_score(n_form):
                tokens_form = set(n_form.split())
                return len(nombre_ab_tokens.intersection(tokens_form))

            # Copia para calcular scores
            temp_df = df_todo_form.copy()
            temp_df["score"] = temp_df["nombre_norm"].apply(calcular_score)
            
            umbral = 2 if len(nombre_ab_tokens) > 1 else 1
            match_candidates = temp_df[temp_df["score"] >= umbral]

        if match_candidates.empty:
            return None, "NO_FOUND"

        # C) PRIORIZACIÓN POR FECHA (Aquí está el arreglo para Fernando)
        # De todos los Fernandos encontrados, ¿hay alguno cuya fecha coincida con hoy?
        match_perfecto = match_candidates[match_candidates[tipo_fecha_col] == fecha_objetivo]

        if not match_perfecto.empty:
            # ¡Bingo! Encontramos al Fernando de HOY
            return match_perfecto.iloc[0], "OK"
        else:
            # Encontramos Fernandos, pero ninguno para hoy. Devolvemos el primero para avisar.
            mejor_match = match_candidates.iloc[0] 
            fecha_erronea = mejor_match[tipo_fecha_col]
            fecha_str = fecha_erronea.strftime('%d/%m') if pd.notnull(fecha_erronea) else "??"
            return mejor_match, f"FECHA_DIFERENTE_{fecha_str}"

    # ==========================================
    # 6. RENDERIZADO
    # ==========================================
    
    if st.session_state.mostrar_resultados:
        fecha_actual = st.session_state.fecha_cursor
        st.divider()
        st.subheader(f"Movimientos del {fecha_actual.strftime('%d/%m/%Y')}")

        ab_entradas = df_airbnb[df_airbnb["fecha_in"] == fecha_actual]
        ab_salidas = df_airbnb[df_airbnb["fecha_out"] == fecha_actual]
        
        codigos_activos = sorted(set(ab_entradas["Codigo_corto"]).union(set(ab_salidas["Codigo_corto"])))

        if not codigos_activos:
            st.info("No hay entradas ni salidas para esta fecha.")
        else:
            for codigo in codigos_activos:
                
                # --- SALIDAS ---
                row_salida = ab_salidas[ab_salidas["Codigo_corto"] == codigo]
                if row_salida.empty:
                    txt_salida = "❌ No hay salida"
                else:
                    huesped = row_salida.iloc[0]
                    nombre_show = formatear_nombre_mostrar(huesped["Nombre del huésped"])
                    
                    # Llamamos a la nueva función inteligente
                    match_row, estado = buscar_match_inteligente(
                        huesped, df_form, "fecha_out", fecha_actual
                    )
                    
                    if estado == "OK":
                        hora = formatear_hora(match_row["Hora de Salida Aprox | Approximate Departure Time"])
                        txt_salida = f"Sale {nombre_show} {hora}"
                    elif estado.startswith("FECHA_DIFERENTE"):
                        fecha_err = estado.split("_")[-1]
                        txt_salida = f"⚠️ Sale {nombre_show} (Form dice: {fecha_err})"
                    else:
                        txt_salida = f"⚠️ Sale {nombre_show} (No llenó form)"

                # --- ENTRADAS ---
                row_entrada = ab_entradas[ab_entradas["Codigo_corto"] == codigo]
                if row_entrada.empty:
                    txt_entrada = "❌ No hay check-in"
                else:
                    huesped = row_entrada.iloc[0]
                    nombre_show = formatear_nombre_mostrar(huesped["Nombre del huésped"])
                    
                    match_row, estado = buscar_match_inteligente(
                        huesped, df_form, "fecha_in", fecha_actual
                    )
                    
                    if estado == "OK":
                        hora = formatear_hora(match_row["Hora de Llegada Aprox | Approximate Arrival Time"])
                        txt_entrada = f"Entra {nombre_show} {hora}"
                    elif estado.startswith("FECHA_DIFERENTE"):
                        fecha_err = estado.split("_")[-1]
                        txt_entrada = f"⚠️ Entra {nombre_show} (Form dice: {fecha_err})"
                    else:
                        txt_entrada = f"⚠️ Entra {nombre_show} (No llenó form)"

                st.markdown(f"**{codigo}**: {txt_salida} / {txt_entrada}")
                st.markdown("---") # Divisor más sutil