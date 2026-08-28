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
            "Entradas y salidas por día",
            "Housekeeping e Inventario"
        ]
    )

# ===== TÍTULO PRINCIPAL =====
st.title("Gestión de Reservas Airbnb")

# =========================
# Subir archivos
# =========================
if menu != "Housekeeping e Inventario":
    archivos = st.file_uploader("📂 Sube tus archivos CSV de Airbnb", type="csv", accept_multiple_files=True)

    if not archivos:
        st.info("Sube al menos un archivo CSV para comenzar")
        st.stop()

    frames = []
    for archivo in archivos:
        df_temp = pd.read_csv(archivo)
        df_temp["__archivo__"] = archivo.name
        frames.append(df_temp)

    df = pd.concat(frames, ignore_index=True)
else:
    df = pd.DataFrame() # Crea un archivo vacío en el fondo para que no dé error

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
if "Hasta" in df.columns:
    df["Hasta"] = pd.to_datetime(df["Hasta"], dayfirst=True, errors="coerce")
    df["Hasta_solo_fecha"] = df["Hasta"].dt.date

# =========================
# Códigos
# =========================
codigo_map = {
    "Central Stay Near Miraflores w/ Pool & Gym": "203 (Surquillo)",
    "Amazing 2BR | City View Balcony | Near San Isidro": "1006 (Surquillo)",
    "Elegant Designer 1BR | Near San Isidro": "307 (Magdalena)",
    "Modern 1BR w/ Pool & Gym Near Miraflores": "508",
    "Luxury Designer 1BR w/ Balcony": "2105 (Jesus Maria)",
    "Amazing View + Pool + Gym - Barranco & Miraflores": "1103",
    "Amazing View 2 + Pool + Gym- Barranco & Miraflores": "1003",
    "Amazing View 3 + Pool + Gym- Barranco & Miraflores": "1415",
    "Amazing View 4 + Pool + Gym- Barranco & Miraflores": "1008",
    "Amazing View 5 + Pool + Gym- Barranco & Miraflores": "1716",
    "Rooftop Pool & Gym | 1BR | Barranco & Miraflores": "1908",
    "Stylish 1BR | Pool & Gym | Near Miraflores": "1010",
    "Amazing 2BR Apart w/ Pool & Gym - Barranco": "810",
    "Modern 2BR with Panoramic City View & Balcony": "1402 (San Isidro)",
    "Park View 2BR w/ Pool & Gym Near San Isidro": "1101 Castilla (Lince)",
    "Ocean View 2BR w/ Pool & Gym & Sauna": "1303 (San Miguel)",
    "Casa increible con AC + Jardín + Centrico": "Casa de Tarapoto",
    "Comfortable 3BR Apartment with City View": "2007 (Pueblo Libre)",
    "Bright 2BR Apartment in Great Location": "401 (Canevaro)",
    "Spacious Designer 1BR w/ Balcony Near San Isidro": "1103 Botanika (Jesús María)"
    "San Bartolo | Vista al mar + Piscina & Gym": "302 MIRA (San Bartolo)"
}

if "Anuncio" in df.columns:
    df["Codigo_corto"] = df["Anuncio"].map(codigo_map).fillna("SIN CODIGO")

    # Orden personalizado de Departamentos ---
    orden_deseado = [
        "1415",
        "1716",
        "1103",
        "1003",
        "1008",
        "1010",
        "508",
        "810",
        "1908",
        "203 (Surquillo)",
        "1006 (Surquillo)",
        "2105 (Jesus Maria)",
        "1103 Botanika (Jesús María)",
        "307 (Magdalena)",
        "Casa de Tarapoto",
        "1402 (San Isidro)",
        "1101 Castilla (Lince)",
        "401 (Canevaro)",
        "1303 (San Miguel)",
        "2007 (Pueblo Libre)",
        "302 MIRA (San Bartolo)",
        "SIN CODIGO" # Lo dejamos al final por si algún día entra un depa nuevo
    ]
    df["Codigo_corto"] = pd.Categorical(df["Codigo_corto"], categories=orden_deseado, ordered=True)

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
            for codigo, grupo in data.groupby('Codigo_corto', observed=True):
                if grupo.empty: continue # Proteccion extra para evitar depas vacios
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

elif menu == "Housekeeping e Inventario":    
    import re
    import datetime

    st.title("Housekeeping e Inventario")
    st.markdown("Control de fugas, lista de compras y consumo por fechas.")

    # --- 1. SUBIDA DE ARCHIVOS ---
    col1, col2 = st.columns(2)
    with col1:
        csv_hk = st.file_uploader("📋 Sube el CSV o ZIP de Housekeeping", type=["csv", "zip"])
    with col2:
        csv_inv = st.file_uploader("📦 Sube el CSV de Inventario Maestro", type="csv")

    if not csv_hk:
        st.info("👆 Sube el reporte diario de Housekeeping para comenzar.")
        st.stop()

    # Soporte para leer ZIP directamente
    import zipfile
    import io
    if csv_hk.name.endswith('.zip'):
        with zipfile.ZipFile(csv_hk) as z:
            nombre_archivo = z.namelist()[0]
            with z.open(nombre_archivo) as f:
                df_hk = pd.read_csv(f)
    else:
        df_hk = pd.read_csv(csv_hk)
    
    # Limpieza de fechas del formulario
    df_hk["Fecha_Real"] = pd.to_datetime(df_hk["Marca temporal"]).dt.date

    # --- TABS (PESTAÑAS PARA ORGANIZAR LA VISTA) ---
    tab1, tab2, tab3 = st.tabs(["🚨 Control Diario (Fugas)", "🛒 Lista de Compras", "📈 Dashboard Mensual"])

    # Función para extraer números ("Más de 2" -> 3)
    def a_numero(val):
        s = str(val).lower()
        if "más de" in s:
            num = re.sub(r"\D", "", s)
            return int(num) + 1 if num else 0
        try:
            return int(float(s))
        except:
            return 0

# --- LÓGICA DE EXTRACCIÓN DEL INVENTARIO MAESTRO ---
    stock_apts = {}
    if csv_inv:
        df_inv = pd.read_csv(csv_inv, header=None, low_memory=False)
        
        # Buscar correctamente la fila de los depas (evitando el título)
        fila_apts = 0
        for i in range(min(20, len(df_inv))):
            texto_fila = " ".join(df_inv.iloc[i].astype(str).fillna("").str.upper())
            if "1103" in texto_fila and "1003" in texto_fila:
                fila_apts = i
                break
        
        # EL GRAN ARREGLO: Diferenciar los dos 1103 y encontrar Tarapoto
        cols_apt = {}
        for col in range(len(df_inv.columns)):
            val = str(df_inv.iloc[fila_apts, col]).upper()
            if "AMAZING" in val:
                nums = re.findall(r'\d{3,4}', val)
                if nums:
                    num = nums[-1]
                    # Si es el 1103 de Jesús María, le ponemos un código especial "1103B"
                    if num == "1103" and "JESUS MARIA" in val:
                        if "1103B" not in cols_apt: 
                            cols_apt["1103B"] = col
                    elif num not in cols_apt:
                        cols_apt[num] = col
                elif "TARAPOTO" in val:
                    cols_apt["TARAPOTO"] = col
        
        traductor_items = {
            "Toallas de mano": "TOALLAS DE MANO",
            "Toallas de cuerpo": "TOALLAS DE CUERPO",
            "Piso de pies": "PISO DE BAÑO",
            "Juego de sábanas": "JUEGO SABANAS",
            "Secador de cocina": "SECADOR DE COCINA"
        }

        # Extraer ideales Y existentes
        for apt, col_idx in cols_apt.items():
            stock_apts[apt] = {}
            for row in range(fila_apts + 1, min(fila_apts + 30, len(df_inv))):
                item_excel = str(df_inv.iloc[row, col_idx]).upper()
                
                for item_form, palabra_clave in traductor_items.items():
                    if palabra_clave in item_excel:
                        valor_ideal = df_inv.iloc[row, col_idx + 1]
                        try:
                            valor_existente = df_inv.iloc[row, col_idx + 2] # Columna EXISTENTE
                        except:
                            valor_existente = ""
                        
                        if pd.notna(valor_existente) and str(valor_existente).strip() != "":
                            stock_apts[apt][item_form] = {
                                'ideal': a_numero(valor_ideal),
                                'existente': a_numero(valor_existente)
                            }

    # ==========================================
    # TAB 1: CONTROL DIARIO Y FUGAS
    # ==========================================
    with tab1:
        st.subheader("Auditoría de Ropa de Cama y Toallas")
        fecha_hk = st.date_input("Selecciona el día a auditar", value=datetime.date.today())
        reportes_hoy = df_hk[df_hk["Fecha_Real"] == fecha_hk]
        
        if reportes_hoy.empty:
            st.warning("No hay reportes de limpieza para esta fecha.")
        else:
            for idx, row in reportes_hoy.iterrows():
                # EL SEGUNDO GRAN ARREGLO: Que el formulario sepa cuál 1103 es cuál
                depa_nombre_upper = str(row["🏠 Departamento"]).upper()
                if "TARAPOTO" in depa_nombre_upper:
                    depa_num = "TARAPOTO"
                elif "1103" in depa_nombre_upper and ("BOTANIKA" in depa_nombre_upper or "JESÚS MARÍA" in depa_nombre_upper or "JESUS MARIA" in depa_nombre_upper):
                    depa_num = "1103B"
                else:
                    nums = re.findall(r'\d{3,4}', depa_nombre_upper)
                    depa_num = nums[0] if nums else "0000"
                
                depa_nombre_mostrar = str(row["🏠 Departamento"])
                personal = str(row["👩‍🔧 Personal de limpieza"])
                obs = str(row["📝 Observaciones"])
                
                st.markdown(f"### 🏠 {depa_nombre_mostrar} - Limpiado por: {personal}")
                if obs and obs.lower() != "nan":
                    st.info(f"**Observaciones:** {obs}")

                items_a_revisar = ["Toallas de mano", "Toallas de cuerpo", "Piso de pies", "Juego de sábanas", "Secador de cocina"]
                
                for item in items_a_revisar:
                    col_limpias = [c for c in df_hk.columns if item.lower() in c.lower() and "limpi" in c.lower()]
                    col_uso = [c for c in df_hk.columns if item.lower() in c.lower() and "uso" in c.lower()]
                    col_sucias = [c for c in df_hk.columns if item.lower() in c.lower() and "suci" in c.lower()]
                    
                    if col_limpias and col_uso and col_sucias:
                        q_limpias_form = a_numero(row[col_limpias[0]])
                        q_uso = a_numero(row[col_uso[0]])
                        q_sucias = a_numero(row[col_sucias[0]])
                        
                        if depa_num in stock_apts and item in stock_apts[depa_num]:
                            existente = stock_apts[depa_num][item]['existente']
                            
                            limpias_calculadas = existente - (q_uso + q_sucias)
                            
                            if limpias_calculadas < 0:
                                estado_fuga = f"🚨 **INCONGRUENCIA:** Reportan {-limpias_calculadas} en uso/sucias MÁS de las que existen."
                                limpias_mostrar = 0
                            elif q_limpias_form == 0 and limpias_calculadas > 0:
                                estado_fuga = "🤖 *Calculado automáticamente (No contaron las limpias)*"
                                limpias_mostrar = limpias_calculadas
                            else:
                                diferencia = limpias_calculadas - q_limpias_form
                                limpias_mostrar = q_limpias_form
                                
                                estado_fuga = "✅ Todo cuadra perfecto"
                                if diferencia > 0:
                                    estado_fuga = f"🚨 **¡FALTAN {diferencia}!** (Reportaron {q_limpias_form} limpias, deberían ser {limpias_calculadas})"
                                elif diferencia < 0:
                                    estado_fuga = f"⚠️ **Sobran {abs(diferencia)}** (Reportaron más de las posibles)"
                                
                            st.markdown(f"**{item}** | Total Excel: **{existente}**")
                            st.markdown(f"↳ **{limpias_mostrar}** limpias (clóset) | **{q_uso}** en uso | **{q_sucias}** sucias")
                            st.caption(f"↳ {estado_fuga}")
                        else:
                            aviso = "*(Aún no subes el Excel)*" if not csv_inv else "*(No cruzado con Excel)*"
                            st.markdown(f"**{item}:** Reportado: {q_limpias_form} limpias | {q_uso} en uso | {q_sucias} sucias {aviso}")
                
                st.divider()

    # ==========================================
    # TAB 2: LISTA DE COMPRAS (RANGO DE FECHAS)
    # ==========================================
    with tab2:
        st.subheader("🛒 Insumos por reponer")
        r_compras = st.date_input("Rango de fechas (desde tu última compra)", value=(datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()), key="rc")
        
        if isinstance(r_compras, tuple) and len(r_compras) == 2:
            df_r = df_hk[(df_hk["Fecha_Real"] >= r_compras[0]) & (df_hk["Fecha_Real"] <= r_compras[1])]
            
            # 1. Función para clasificar zonas mágicamente
            def clasificar_zona(depa_str):
                d = depa_str.upper()
                if "TARAPOTO" in d: return "Tarapoto"
                if "203" in d: return "Surquillo"
                if "307" in d: return "Magdalena"
                if "2105" in d: return "Jesús María"
                if "1103" in d and ("BOTANIKA" in d or "JESÚS" in d or "JESUS" in d): return "Jesús María"
                return "Barranco" # 1415, 1716, 1103, 1003, 1008, 1010, 508, 810
                
            # 2. Agrupar datos por departamento y por ZONA (Para el Total)
            datos_compras = {}
            resumen_zonas = {} # NUEVO: Guardará los totales por zona sin repetir
            
            for _, r in df_r.iterrows():
                depa_nombre_real = str(r['🏠 Departamento'])
                zona = clasificar_zona(depa_nombre_real)
                fecha_str = r['Fecha_Real'].strftime('%d/%m')
                
                if depa_nombre_real not in datos_compras:
                    datos_compras[depa_nombre_real] = {'zona': zona, 'productos': {}}
                
                if zona not in resumen_zonas:
                    resumen_zonas[zona] = set() # Usamos un 'set' para que no hayan duplicados
                    
                for col in ["¿Qué se está acabando o falta de PRODUCTOS DE LIMPIEZA?", "¿Qué se está acabando o falta de AMENITIES?"]:
                    if pd.notna(r[col]):
                        for prod in str(r[col]).split(";"):
                            p = prod.strip().capitalize() # Pone la primera letra en mayúscula
                            if p:
                                # Agregar al detalle del depa
                                if p not in datos_compras[depa_nombre_real]['productos']:
                                    datos_compras[depa_nombre_real]['productos'][p] = []
                                datos_compras[depa_nombre_real]['productos'][p].append(fecha_str)
                                
                                # Agregar al TOTAL de la zona
                                resumen_zonas[zona].add(p)

            if not datos_compras:
                st.success("¡Todo en orden en estas fechas! No hay faltantes reportados.")
            else:
                # 3. Filtros Interactivos
                col_f1, col_f2 = st.columns(2)
                zonas_disponibles = ["Todas"] + sorted(list(set(d['zona'] for d in datos_compras.values())))
                
                with col_f1:
                    filtro_zona = st.selectbox("📍 Filtrar por Zona", zonas_disponibles)
                
                depas_filtrados = [depa for depa, datos in datos_compras.items() if filtro_zona == "Todas" or datos['zona'] == filtro_zona]
                
                with col_f2:
                    filtro_depa = st.selectbox("🏠 Filtrar por Departamento", ["Todos"] + sorted(depas_filtrados))
                
                st.markdown("---")
                
                # ========================================
                # NUEVO: RESUMEN TOTAL PARA EL SUPERMERCADO
                # ========================================
                if filtro_depa == "Todos":
                    st.markdown("### 🛒 Resumen Total para el Supermercado")
                    st.caption("Lista rápida y sin repetidos agrupada por zona.")
                    
                    for z in sorted(resumen_zonas.keys()):
                        if filtro_zona == "Todas" or filtro_zona == z:
                            prods_zona = sorted(list(resumen_zonas[z]))
                            if prods_zona:
                                st.success(f"**📍 {z}:** {', '.join(prods_zona)}")
                                
                    st.markdown("---")
                    st.markdown("### 🏠 Desglose detallado por Departamento")
                # ========================================

                # 4. Mostrar Resultados Estilo Dashboard (Detalles)
                mostrados = 0
                for depa in sorted(depas_filtrados):
                    if filtro_depa != "Todos" and depa != filtro_depa:
                        continue
                        
                    prods = datos_compras[depa]['productos']
                    if prods:
                        mostrados += 1
                        nombres_prods = list(prods.keys())
                        
                        st.markdown(f"#### 🏠 {depa}")
                        st.warning(f"**Faltan:** {', '.join(nombres_prods)}")
                        
                        # Detalles ocultos con "Ver más"
                        with st.expander("👀 Ver historial de solicitudes para este depa"):
                            for p, fechas in prods.items():
                                conteo = len(fechas)
                                veces_txt = f"*(Solicitado {conteo} veces)*" if conteo > 1 else ""
                                st.write(f"- **{p}:** el {', '.join(fechas)} {veces_txt}")
                        st.write("") # Espaciador
                
                if mostrados == 0:
                    st.info("No hay faltantes para los filtros seleccionados.")

    # ==========================================
    # TAB 3: DASHBOARD DE CONSUMOS (RANGO)
    # ==========================================
    with tab3:
        st.subheader("📊 Gastos y Consumos")
        
        # Por defecto muestra del día 1 del mes actual, hasta hoy
        primer_dia_mes = datetime.date.today().replace(day=1)
        rango_consumo = st.date_input(
            "Selecciona el rango de fechas a analizar", 
            value=(primer_dia_mes, datetime.date.today()),
            key="rango_consumos"
        )
        
        if isinstance(rango_consumo, tuple) and len(rango_consumo) == 2:
            f_inicio, f_fin = rango_consumo
            df_rango = df_hk[(df_hk["Fecha_Real"] >= f_inicio) & (df_hk["Fecha_Real"] <= f_fin)].copy()
            
            if df_rango.empty:
                st.info("No hay datos de consumo para este rango de fechas.")
            else:
                col_ph = "🧻 Cantidad de papel higiénico repuesto hoy (rollos)"
                col_pt = "🧻 Papel toalla respuesto (rollos)"
                col_jb = "🧼 Cantidad de jabones repuestos hoy"
                
                total_ph = sum(df_rango[col_ph].apply(a_numero))
                total_pt = sum(df_rango[col_pt].apply(a_numero))
                total_jb = sum(df_rango[col_jb].apply(a_numero))
                
                c1, c2, c3 = st.columns(3)
                c1.metric(label="🧻 Papel Higiénico Total", value=f"{total_ph} ud.")
                c2.metric(label="🧻 Papel Toalla Total", value=f"{total_pt} ud.")
                c3.metric(label="🧼 Jabones Totales", value=f"{total_jb} ud.")
                
                st.markdown("---")
                st.markdown("**Desglose de Consumo por Departamento (Rango seleccionado):**")
                
                df_rango["PH"] = df_rango[col_ph].apply(a_numero)
                df_rango["PT"] = df_rango[col_pt].apply(a_numero)
                df_rango["JB"] = df_rango[col_jb].apply(a_numero)
                
                consumo_depas = df_rango.groupby("🏠 Departamento")[["PH", "PT", "JB"]].sum().reset_index()
                consumo_depas.columns = ["Departamento", "Papel Higiénico", "Papel Toalla", "Jabones"]
                
                st.dataframe(consumo_depas.sort_values("Papel Higiénico", ascending=False), use_container_width=True)