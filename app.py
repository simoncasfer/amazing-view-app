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
# Normalizar CSV de Airbnb (viejo "Reservas" o nuevo "Ingresos > Próximos")
# =========================
def normalizar_reservas(df_raw):
    """
    Airbnb dejó de ofrecer el CSV clásico de 'Lista de reservas'.
    Ahora exporta reportes de Ingresos (Próximos), que tienen columnas
    distintas. Esta función detecta cuál formato es y lo convierte a la
    misma estructura que ya usa el resto del programa (Estado, Anuncio,
    Hasta, 'Nombre del huésped', 'Fecha de inicio', etc.)
    """
    df_raw = df_raw.copy()

    es_formato_nuevo = "Huésped" in df_raw.columns and "Tipo" in df_raw.columns

    if not es_formato_nuevo:
        return df_raw  # Formato viejo: no se toca nada

    # Solo nos interesan filas que son una estadía real.
    # 'Cobro como coanfitrión', 'Ajuste', 'Pago de la resolución', etc.
    # son movimientos de dinero, no huéspedes.
    if "Tipo" in df_raw.columns:
        df_raw = df_raw[df_raw["Tipo"].astype(str).str.strip() == "Reservación"].copy()

    df_raw = df_raw.rename(columns={
        "Huésped": "Nombre del huésped",
        "Fecha de finalización": "Hasta",
    })

    # OJO: el CSV nuevo (Ingresos) trae las fechas en formato
    # mes/día/año (americano), a diferencia del CSV viejo que era
    # día/mes/año. Si no se convierten aquí, el resto del programa
    # las lee con dayfirst=True y las interpreta MAL (ej. 09/03/2026
    # = 3 de septiembre, se leía como 9 de marzo).
    for col in ["Fecha de inicio", "Hasta"]:
        if col in df_raw.columns:
            df_raw[col] = pd.to_datetime(df_raw[col], format="%m/%d/%Y", errors="coerce")

    # Columnas que el CSV nuevo no trae: se rellenan con valores neutros
    # para que el resto del código no se rompa.
    if "Estado" not in df_raw.columns:
        df_raw["Estado"] = "Confirmada"  # Ingresos ya no incluye canceladas

    for col in ["Número de adultos", "Número de niños", "Número de bebés"]:
        if col not in df_raw.columns:
            df_raw[col] = 0

    return df_raw


# =========================
# Funciones compartidas para cruzar Airbnb <-> Formulario de Check-in
# (las usan tanto "Lista de huéspedes por departamento" como
#  "Entradas y salidas por día")
# =========================
import unicodedata
import re as _re
from difflib import SequenceMatcher


def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = texto.replace("-", " ")
    texto = _re.sub(r"[^a-z0-9\s]", "", texto)
    texto = _re.sub(r"\s+", " ", texto).strip()
    return texto


def limpiar_dni(dni):
    if pd.isna(dni):
        return ""
    dni_str = str(dni).strip()
    if dni_str.endswith(".0"):
        dni_str = dni_str[:-2]
    return dni_str


def formatear_nombre_mostrar(nombre_completo):
    if pd.isna(nombre_completo):
        return "Huésped"
    tokens = str(nombre_completo).strip().split()
    if len(tokens) >= 2:
        return f"{tokens[0].title()} {tokens[1].title()}"
    elif tokens:
        return tokens[0].title()
    return "Huésped"


def formatear_hora(hora_raw):
    if pd.isna(hora_raw):
        return "??"
    try:
        return hora_raw.strftime("%I:%M %p").lower().replace(":00", "")
    except Exception:
        s = str(hora_raw).lower()
        return s.replace(":00", "").replace(".", "")


COL_LLEGADA_FORM = "Fecha de Llegada | Arrival Date"
COL_SALIDA_FORM = "Fecha de Salida | Departure Date"
COL_DNI_FORM = "N° Documento de Identidad o Pasaporte | N° ID or Passport"
COL_NOMBRE_FORM = "Nombre completo | Full Name"
COL_DNI_AIRBNB = "N° Documento de Identidad o Pasaporte"


def preparar_df_form(df_form_raw):
    """Agrega las columnas normalizadas que se usan para cruzar con Airbnb."""
    df_form = df_form_raw.copy()
    df_form["fecha_in"] = pd.to_datetime(df_form[COL_LLEGADA_FORM], dayfirst=True, errors="coerce").dt.date
    df_form["fecha_out"] = pd.to_datetime(df_form[COL_SALIDA_FORM], dayfirst=True, errors="coerce").dt.date
    df_form["dni_clean"] = df_form[COL_DNI_FORM].apply(limpiar_dni)
    df_form["nombre_norm"] = df_form[COL_NOMBRE_FORM].apply(normalizar_texto)
    return df_form


def preparar_df_airbnb_para_cruce(df_airbnb_raw):
    df_airbnb = df_airbnb_raw.copy()
    df_airbnb["fecha_in"] = pd.to_datetime(df_airbnb["Fecha de inicio"], dayfirst=True, errors="coerce").dt.date
    df_airbnb["fecha_out"] = pd.to_datetime(df_airbnb["Hasta"], dayfirst=True, errors="coerce").dt.date
    if COL_DNI_AIRBNB in df_airbnb.columns:
        df_airbnb["dni_clean"] = df_airbnb[COL_DNI_AIRBNB].apply(limpiar_dni)
    else:
        df_airbnb["dni_clean"] = ""
    df_airbnb["nombre_norm"] = df_airbnb["Nombre del huésped"].apply(normalizar_texto)
    return df_airbnb


def expandir_candidatos_form(df_form):
    """
    El formulario permite registrar hasta 4 huéspedes por reserva (titular +
    3 acompañantes). El nombre que Airbnb muestra puede ser el de
    CUALQUIERA de ellos (a veces el que reserva no es el mismo que llena
    el form, o llena el form el acompañante). Esta función crea una fila
    candidata por cada huésped nombrado, todas apuntando a la misma
    reserva/fecha original, para poder buscar coincidencias con cualquiera
    de los nombres, no solo el del titular.
    """
    filas = []
    for idx, row in df_form.iterrows():
        for suf in ["", ".1", ".2", ".3"]:
            col_nombre = f"{COL_NOMBRE_FORM}{suf}"
            col_dni = f"{COL_DNI_FORM}{suf}"
            if col_nombre not in df_form.columns:
                continue
            nombre_val = row[col_nombre]
            if pd.isna(nombre_val) or str(nombre_val).strip() == "":
                continue
            filas.append({
                "nombre_norm": normalizar_texto(nombre_val),
                "dni_clean": limpiar_dni(row[col_dni]) if col_dni in df_form.columns else "",
                "fecha_in": row["fecha_in"],
                "fecha_out": row["fecha_out"],
                "__form_idx__": idx,
            })
    return pd.DataFrame(filas)


def _score_nombre(tokens_ab, n_form):
    """Puntaje por palabras en común + similitud aproximada (typos/apodos)."""
    if not tokens_ab or not n_form:
        # Si no hay nada que comparar de un lado (ej. nombre en otro
        # alfabeto que quedó vacío al limpiar el texto), NO se puede
        # decir que "se parece" a nada -> evita falsos positivos entre
        # dos nombres vacíos.
        return 0
    tokens_form = set(n_form.split())
    if not tokens_form:
        return 0
    overlap = len(tokens_ab.intersection(tokens_form))
    if overlap > 0:
        return overlap * 10
    # Nada en común palabra por palabra: probamos similitud aproximada
    # (útil para "Jose Perez" vs "J. Perez Gomez", tildes raras, etc.)
    ratio = SequenceMatcher(None, " ".join(sorted(tokens_ab)), n_form).ratio()
    return ratio * 5 if ratio >= 0.55 else 0


def buscar_match_inteligente(row_airbnb, df_form_completo, df_candidatos, tipo_fecha_col, fecha_objetivo):
    """
    Busca la fila del formulario que corresponde a esta reserva de Airbnb.
    Compara contra TODOS los huéspedes nombrados en cada formulario
    (titular + hasta 3 acompañantes, vía df_candidatos), porque el nombre
    de Airbnb puede corresponder a cualquiera de ellos.

    Prueba varias señales, de la más confiable a la menos confiable, porque
    en la práctica: el nombre de Airbnb no siempre es el del huésped real
    que llena el form (reserva a nombre de otra persona), hay nombres
    parecidos entre reservas distintas, etc.

      1) DNI exacto (de cualquiera de los huéspedes)        -> "OK_DNI"
      2) Nombre (con palabras en común o similar, de         -> "OK_NOMBRE"
         cualquier huésped) + fecha exacta coinciden
      3) Fecha de entrada Y salida coinciden EXACTO y hay   -> "OK_FECHA"
         un único formulario con esa combinación (aunque
         el nombre no calce - reserva a nombre de otro)
      4) Mejor nombre parecido encontrado, aunque la fecha  -> "FECHA_DIFERENTE_xx"
         no coincida (se muestra como advertencia, no como
         "no llenó el form")

    Devuelve siempre la fila COMPLETA del formulario original (no solo el
    candidato), para poder leer horas, contar acompañantes, etc.
    """
    dni_ab = row_airbnb.get("dni_clean", "")
    fin_ab = row_airbnb.get("fecha_in")
    fout_ab = row_airbnb.get("fecha_out")
    nombre_ab_tokens = set(str(row_airbnb.get("nombre_norm", "")).split())

    def _fila_completa(idx_form):
        return df_form_completo.loc[idx_form]

    # 1) DNI exacto (de cualquiera de los huéspedes nombrados)
    if isinstance(dni_ab, str) and len(dni_ab) > 4:
        cand_dni = df_candidatos[df_candidatos["dni_clean"] == dni_ab]
        if not cand_dni.empty:
            return _fila_completa(cand_dni.iloc[0]["__form_idx__"]), "OK_DNI"

    # Candidatos por nombre (con score de similitud), contra CUALQUIER
    # huésped nombrado del formulario, no solo el titular
    temp = df_candidatos.copy()
    temp["score"] = temp["nombre_norm"].apply(lambda n: _score_nombre(nombre_ab_tokens, n))
    umbral = 10 if len(nombre_ab_tokens) > 1 else 5
    cand_nombre = temp[temp["score"] >= umbral].copy()

    def _ordenar_por_score_y_cercania(cand):
        """Si dos formularios comparten nombre (ej. la persona lo llenó dos
        veces con datos distintos), preferimos el que tenga la fecha más
        cercana a la fecha real de Airbnb, en vez del primero por índice."""
        def _dist(f):
            if pd.isna(f) or pd.isna(fecha_objetivo):
                return 99999
            return abs((f - fecha_objetivo).days)
        cand = cand.copy()
        cand["_dist"] = cand[tipo_fecha_col].apply(_dist)
        return cand.sort_values(["score", "_dist"], ascending=[False, True])

    # 2) Nombre parecido + fecha exacta
    if not cand_nombre.empty:
        match_exacto = cand_nombre[cand_nombre[tipo_fecha_col] == fecha_objetivo]
        if not match_exacto.empty:
            mejor = _ordenar_por_score_y_cercania(match_exacto).iloc[0]
            return _fila_completa(mejor["__form_idx__"]), "OK_NOMBRE"

    # 3) Si SÍ hay candidato por nombre pero su fecha no calza, hay que
    #    devolver A ESA PERSONA con el aviso de fecha distinta — NUNCA
    #    saltar a otro desconocido solo porque comparte fechas (eso
    #    generaba el bug de mostrarle a Cecilia la hora de otro huésped).
    if not cand_nombre.empty:
        mejor = _ordenar_por_score_y_cercania(cand_nombre).iloc[0]
        fecha_err = mejor[tipo_fecha_col]
        fecha_str = fecha_err.strftime('%d/%m') if pd.notnull(fecha_err) else "no registrada"
        return _fila_completa(mejor["__form_idx__"]), f"FECHA_DIFERENTE_{fecha_str}"

    # 4) Nadie con nombre parecido: como último recurso, si AMBAS fechas
    #    (entrada y salida) calzan exacto con un único formulario, lo
    #    tomamos como la típica "reserva a nombre de otra persona".
    if pd.notnull(fin_ab) and pd.notnull(fout_ab):
        cand_fecha = df_form_completo[
            (df_form_completo["fecha_in"] == fin_ab) & (df_form_completo["fecha_out"] == fout_ab)
        ]
        if len(cand_fecha) == 1:
            return cand_fecha.iloc[0], "OK_FECHA"

    return None, "NO_FOUND"


def contar_huespedes_extra_form(form_row):
    """
    Cuenta cuántos huéspedes ADICIONALES (sin contar al titular) registró
    el formulario, usando los bloques repetidos 'Nombre completo | Full Name.N'
    que aparecen cuando marcan '¿Se hospedará otro huésped más?'.
    Devuelve None si no hay fila de formulario (para no confundir "0 extra"
    con "no sabemos").
    """
    if form_row is None:
        return None
    extra = 0
    for suf in [".1", ".2", ".3"]:
        col = f"{COL_NOMBRE_FORM}{suf}"
        if col in form_row.index:
            valor = form_row[col]
            if pd.notna(valor) and str(valor).strip() != "":
                extra += 1
    return extra


# =========================
# Subir archivos
# =========================
if menu != "Housekeeping e Inventario":
    archivos = st.file_uploader("📂 Sube tus archivos CSV de Airbnb (Reservas viejo o Ingresos > Próximos)", type="csv", accept_multiple_files=True)

    if not archivos:
        st.info("Sube al menos un archivo CSV para comenzar")
        st.stop()

    frames = []
    for archivo in archivos:
        df_temp = pd.read_csv(archivo, encoding="utf-8-sig")
        df_temp = normalizar_reservas(df_temp)
        df_temp["__archivo__"] = archivo.name
        frames.append(df_temp)

    df = pd.concat(frames, ignore_index=True)

    # Por si subes el mismo mes/cuenta dos veces sin querer
    if "Código de confirmación" in df.columns:
        df = df.drop_duplicates(subset=["Código de confirmación"], keep="first")
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
    "Amazing 2BR | Rooftop Pool + Gym | Near San Isidro": "1006 (Surquillo)",
    "Elegant Designer 1BR | Near San Isidro": "307 (Magdalena)",
    "Modern 1BR w/ Pool & Gym Near Miraflores": "508",
    "Apartamento de diseño + balcón · Cerca San Isidro": "2105 (Jesus Maria)",
    "Amazing View + Pool + Gym - Barranco & Miraflores": "1103",
    "Amazing View 2 + Pool + Gym- Barranco & Miraflores": "1003",
    "Amazing View 3 + Pool + Gym- Barranco & Miraflores": "1415",
    "Amazing View 4 + Pool + Gym- Barranco & Miraflores": "1008",
    "Amazing View 5 + Pool + Gym- Barranco & Miraflores": "1716",
    "Rooftop Pool & City View · Modern 1BR Barranco": "1908",
    "Stylish 1BR | Pool & Gym | Near Miraflores": "1010",
    "Amazing 2BR Apart w/ Pool & Gym - Barranco": "810",
    "Modern 2BR with Panoramic City View & Balcony": "1402 (San Isidro)",
    "Park View 2BR w/ Pool & Gym Near San Isidro": "1101 Castilla (Lince)",
    "Despierta frente al mar · 2 hab, piscina y sauna": "1303 (San Miguel)",
    "Casa increible con AC + Jardín + Centrico": "Casa de Tarapoto",
    "Familiar 3 hab, 2 baños y vista · Pueblo Libre": "2007 (Pueblo Libre)",
    "Amplio apartamento 2 hab, 2 baños · Lince céntrico": "401 (Canevaro)",
    "Diseño con balcón y vista · 1BR cerca San Isidro": "1103 Botanika (Jesús María)",
    "Vista al mar | Piscina | 2 hab | San Bartolo": "302 MIRA (San Bartolo)"
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

        # Preparamos el cruce con el formulario (si ya lo subieron) para
        # sacar el +N real de huéspedes adicionales, en vez de depender
        # de "Número de adultos/niños/bebés" (que el CSV nuevo de Airbnb
        # ya no trae).
        df_form_prep = None
        df_candidatos = None
        if "df_form" in st.session_state:
            df_form_prep = preparar_df_form(st.session_state.df_form)
            df_candidatos = expandir_candidatos_form(df_form_prep)
            data = preparar_df_airbnb_para_cruce(data)

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

                    extra_txt = ""
                    if df_form_prep is not None:
                        match_row, estado = buscar_match_inteligente(
                            r, df_form_prep, df_candidatos, "fecha_in", r.get("fecha_in")
                        )
                        extra_n = contar_huespedes_extra_form(match_row)
                        if extra_n is not None and extra_n > 0:
                            extra_txt = f" +{extra_n}"
                    else:
                        # Sin formulario cargado: fallback al conteo viejo
                        # (solo funciona si el CSV trae adultos/niños/bebés)
                        total = int(r['Total_huespedes'])
                        extra_txt = f" +{total-1}" if total > 1 else ""

                    st.write(f"{desde}-{hasta}: {nombre}{extra_txt}")


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
    # 2 y 3. PREPARACIÓN DE DATOS (usando funciones compartidas)
    # ==========================================
    df_form = preparar_df_form(df_form)
    df_candidatos = expandir_candidatos_form(df_form)
    df_airbnb = preparar_df_airbnb_para_cruce(df_airbnb)

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

    # (la función buscar_match_inteligente ahora es compartida, definida
    # arriba junto con normalizar_reservas, para poder usarla también en
    # "Lista de huéspedes por departamento")

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
                        huesped, df_form, df_candidatos, "fecha_out", fecha_actual
                    )
                    
                    if estado.startswith("OK"):
                        hora = formatear_hora(match_row["Hora de Salida Aprox (Antes de 11:00 am) | Approximate Departure Time (Before 11:00 am)"])
                        aviso = " (nombre distinto en form)" if estado == "OK_FECHA" else ""
                        txt_salida = f"Sale {nombre_show} {hora}{aviso}"
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
                        huesped, df_form, df_candidatos, "fecha_in", fecha_actual
                    )
                    
                    if estado.startswith("OK"):
                        hora = formatear_hora(match_row["Hora de Llegada (Despues de 3:00 pm) | Approximate Arrival Time (After 3:00 pm)"])
                        aviso = " (nombre distinto en form)" if estado == "OK_FECHA" else ""
                        txt_entrada = f"Entra {nombre_show} {hora}{aviso}"
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