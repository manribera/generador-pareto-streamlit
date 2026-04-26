import os
import tempfile
from io import BytesIO, StringIO
from datetime import datetime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak
)


st.set_page_config(
    page_title="Generador de Informe Pareto",
    layout="wide"
)

AZUL = colors.HexColor("#0B3A53")
VERDE = colors.HexColor("#2E7D32")
DORADO = colors.HexColor("#C9A227")
GRIS_CLARO = colors.HexColor("#F2F6F8")
GRIS_BORDE = colors.HexColor("#CBD5DF")


TABLA_VACIA = "Descriptor priorizado\tFrecuencia"

TABLA_EJEMPLO = """Descriptor priorizado\tFrecuencia
Consumo de drogas\t1787
Estafa o defraudación\t637
Robo a personas\t587
Falta de inversión social\t544
Hurto\t508
Deficiencia en la infraestructura vial\t476
Venta de drogas\t472
Personas en situación de calle\t358
Consumo de alcohol en vía pública\t343
Robo a vehículos (tacha)\t343
Disturbios (riñas)\t325
Daños/vandalismo\t316
Puntos de venta y consumo de drogas\t314
Robo a comercio (tacha)\t305
Robo a comercio (intimidación)\t299
Lesiones\t275
Robo a vivienda (tacha)\t233
Homicidio\t224
Violencia intrafamiliar\t210
Robo de vehículos\t168
Delitos sexuales\t152
Falta de salubridad pública\t151
Robo de motocicletas/vehículos (bajonazo)\t148
Deficiencias en el alumbrado público\t147"""


if "tabla_texto_actual" not in st.session_state:
    st.session_state.tabla_texto_actual = TABLA_EJEMPLO

if "tabla_texto_widget" not in st.session_state:
    st.session_state.tabla_texto_widget = st.session_state.tabla_texto_actual

if "modo_ingreso" not in st.session_state:
    st.session_state.modo_ingreso = "Pegar tabla"

if "datos_limpiados" not in st.session_state:
    st.session_state.datos_limpiados = False


def limpiar_numero(valor):
    try:
        valor = str(valor).replace("%", "").replace(",", ".").strip()
        valor = "".join(c for c in valor if c.isdigit() or c == ".")
        return float(valor) if valor else 0
    except Exception:
        return 0


def limpiar_nombre_archivo(texto):
    texto = str(texto)
    caracteres_no_validos = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]

    for c in caracteres_no_validos:
        texto = texto.replace(c, "")

    texto = texto.replace("Delegación", "")
    texto = texto.replace("Delegacion", "")
    texto = texto.replace("delegación", "")
    texto = texto.replace("delegacion", "")
    texto = texto.replace("_", " ")
    texto = " ".join(texto.split())

    return texto.strip()


def leer_tabla_pegada(texto):
    texto = texto.strip()

    if not texto or texto == TABLA_VACIA:
        return pd.DataFrame(columns=["Descriptor priorizado", "Frecuencia"])

    try:
        df = pd.read_csv(StringIO(texto), sep="\t")
    except Exception:
        try:
            df = pd.read_csv(StringIO(texto), sep=";")
        except Exception:
            df = pd.read_csv(StringIO(texto), sep=",")

    df.columns = [str(c).strip() for c in df.columns]

    if len(df.columns) < 2:
        return pd.DataFrame(columns=["Descriptor priorizado", "Frecuencia"])

    col_descriptor = df.columns[0]
    col_frecuencia = df.columns[1]

    for col in df.columns:
        nombre = str(col).lower().strip()

        if "descriptor" in nombre or "problem" in nombre:
            col_descriptor = col

        if "frecuencia" in nombre or "cantidad" in nombre or "casos" in nombre:
            col_frecuencia = col

    df = df[[col_descriptor, col_frecuencia]].copy()
    df.columns = ["Descriptor priorizado", "Frecuencia"]

    df["Descriptor priorizado"] = df["Descriptor priorizado"].astype(str).str.strip()
    df["Frecuencia"] = df["Frecuencia"].apply(limpiar_numero).astype(int)

    df = df[df["Descriptor priorizado"] != ""]
    df = df[df["Descriptor priorizado"].str.lower() != "nan"]
    df = df[df["Frecuencia"] > 0]

    df = df.sort_values("Frecuencia", ascending=False).reset_index(drop=True)

    return df


def procesar_df(df, total_general):
    df = df.copy()

    df["Descriptor priorizado"] = df["Descriptor priorizado"].astype(str).str.strip()
    df["Frecuencia"] = pd.to_numeric(df["Frecuencia"], errors="coerce").fillna(0).astype(int)

    df = df[df["Descriptor priorizado"] != ""]
    df = df[df["Descriptor priorizado"].str.lower() != "nan"]
    df = df[df["Frecuencia"] > 0]
    df = df.sort_values("Frecuencia", ascending=False).reset_index(drop=True)

    if total_general > 0:
        df["Porcentaje"] = (df["Frecuencia"] / total_general) * 100
    else:
        df["Porcentaje"] = 0

    df["Porcentaje acumulado"] = df["Porcentaje"].cumsum()

    return df


def crear_grafico_pareto(df):
    fig, ax1 = plt.subplots(figsize=(13.5, 7.2))

    color_barras = "#1B9E77"
    color_linea = "#0B3A53"

    x = list(range(len(df)))

    ax1.bar(
        x,
        df["Frecuencia"],
        color=color_barras,
        edgecolor="#0B3A53",
        linewidth=0.4
    )

    ax1.set_ylabel("Frecuencia", fontsize=9)
    ax1.set_xlabel("Descriptor priorizado", fontsize=8)

    ax1.set_xticks(x)
    ax1.set_xticklabels(
        df["Descriptor priorizado"],
        rotation=90,
        ha="center",
        va="top",
        fontsize=6.4
    )

    ax1.tick_params(axis="y", labelsize=8)
    ax1.grid(axis="y", linestyle="--", alpha=0.35)

    ax2 = ax1.twinx()
    ax2.plot(
        x,
        df["Porcentaje acumulado"],
        color=color_linea,
        marker="o",
        linewidth=1.8,
        markersize=3.5
    )

    ax2.set_ylabel("% acumulado", fontsize=9)
    ax2.set_ylim(0, 100)
    ax2.tick_params(axis="y", labelsize=8)

    plt.title(
        "Pareto priorizado - Pareto general portafolio",
        fontsize=10,
        color="#0B3A53",
        pad=8
    )

    fig.subplots_adjust(bottom=0.45)
    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=220, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)

    return buffer


def encabezado_pagina(canvas, doc):
    canvas.saveState()
    width, height = letter

    canvas.setFillColor(AZUL)
    canvas.rect(0, height - 45, width, 45, fill=True, stroke=False)

    canvas.setFillColor(VERDE)
    canvas.rect(0, height - 50, width, 5, fill=True, stroke=False)

    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 40, 25, f"Página {doc.page}")

    canvas.restoreState()


def portada_pdf(story, styles, datos, logo_path):
    if os.path.exists(logo_path):
        img = Image(logo_path, width=2.5 * inch, height=2.0 * inch)
        img.hAlign = "CENTER"
        story.append(Spacer(1, 0.45 * inch))
        story.append(img)
    else:
        story.append(Spacer(1, 1.3 * inch))

    story.append(Spacer(1, 0.35 * inch))

    story.append(Paragraph(datos["titulo"], styles["TituloPortada"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(datos["subtitulo"], styles["SubtituloPortada"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(datos["tipo_pareto"], styles["TipoPareto"]))
    story.append(Spacer(1, 0.20 * inch))
    story.append(Paragraph(datos["delegacion"], styles["SubtituloPortada"]))

    story.append(Spacer(1, 0.45 * inch))
    story.append(Paragraph(datos["programa"], styles["TextoCentro"]))
    story.append(Spacer(1, 0.10 * inch))
    story.append(Paragraph(f"Fecha de emisión: {datos['fecha_emision']}", styles["TextoCentro"]))

    story.append(Spacer(1, 0.65 * inch))

    nota = Table(
        [[Paragraph(datos["nota_tecnica"], styles["Nota"])]],
        colWidths=[6.6 * inch]
    )

    nota.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF5F9")),
        ("BOX", (0, 0), (-1, -1), 0.7, GRIS_BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    story.append(nota)
    story.append(PageBreak())


def tabla_priorizados_pdf(df, styles):
    data = [["Descriptor priorizado", "Frecuencia", "Porcentaje", "Porcentaje acumulado"]]

    for _, row in df.iterrows():
        data.append([
            Paragraph(str(row["Descriptor priorizado"]), styles["CeldaTabla"]),
            f"{int(row['Frecuencia'])}",
            f"{row['Porcentaje']:.2f}%",
            f"{row['Porcentaje acumulado']:.2f}%"
        ])

    total_priorizado = int(df["Frecuencia"].sum())

    data.append([
        Paragraph("Total priorizado", styles["CeldaTablaNegrita"]),
        str(total_priorizado),
        "",
        ""
    ])

    table = Table(
        data,
        colWidths=[3.75 * inch, 1.0 * inch, 1.05 * inch, 1.35 * inch],
        repeatRows=1
    )

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1F2933")),

        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C7D3")),

        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DDEFE7")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#0B3A53")),
    ]

    for i in range(1, len(data) - 1):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#EAF2F7")))
        else:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.white))

    table.setStyle(TableStyle(style))

    return table


def generar_pdf(datos, df, texto_resultados):
    buffer_pdf = BytesIO()

    doc = SimpleDocTemplate(
        buffer_pdf,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=70,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="TituloPortada",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=AZUL,
        fontSize=25,
        leading=30,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="SubtituloPortada",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#2B4A5A"),
        fontSize=13,
        leading=17
    ))

    styles.add(ParagraphStyle(
        name="TipoPareto",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=VERDE,
        fontSize=16,
        leading=20,
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="TextoCentro",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=11,
        leading=15
    ))

    styles.add(ParagraphStyle(
        name="Nota",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#263238")
    ))

    styles.add(ParagraphStyle(
        name="TituloSeccion",
        parent=styles["Heading2"],
        textColor=AZUL,
        fontSize=15,
        leading=18,
        spaceBefore=10,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="Parrafo",
        parent=styles["Normal"],
        alignment=TA_JUSTIFY,
        fontSize=10,
        leading=15,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="Resultado",
        parent=styles["Normal"],
        alignment=TA_JUSTIFY,
        fontSize=10,
        leading=15,
        leftIndent=8,
        rightIndent=8,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="CeldaTabla",
        parent=styles["Normal"],
        fontSize=8,
        leading=10
    ))

    styles.add(ParagraphStyle(
        name="CeldaTablaNegrita",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        fontName="Helvetica-Bold"
    ))

    story = []
    logo_path = "001.png"

    portada_pdf(story, styles, datos, logo_path)

    story.append(Paragraph("Introducción", styles["TituloSeccion"]))
    story.append(Paragraph(datos["introduccion_1"], styles["Parrafo"]))
    story.append(Paragraph(datos["introduccion_2"], styles["Parrafo"]))

    story.append(Spacer(1, 0.10 * inch))
    story.append(Paragraph("Resultados generales", styles["TituloSeccion"]))

    caja_resultados = Table(
        [[Paragraph(texto_resultados, styles["Resultado"])]],
        colWidths=[6.7 * inch]
    )

    caja_resultados.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F6F8")),
        ("BOX", (0, 0), (-1, -1), 0.7, GRIS_BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(caja_resultados)

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Figura 1. Pareto priorizado - Pareto general portafolio.", styles["Parrafo"]))

    chart_buffer = crear_grafico_pareto(df)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(chart_buffer.getvalue())
        chart_path = tmp.name

    chart_img = Image(chart_path, width=6.7 * inch, height=3.55 * inch)
    chart_img.hAlign = "CENTER"
    story.append(chart_img)

    story.append(PageBreak())

    story.append(Paragraph("Tabla de descriptores priorizados", styles["TituloSeccion"]))
    story.append(tabla_priorizados_pdf(df, styles))

    story.append(PageBreak())

    story.append(Spacer(1, 1.4 * inch))

    if os.path.exists(logo_path):
        img_final = Image(logo_path, width=2.8 * inch, height=2.2 * inch)
        img_final.hAlign = "CENTER"
        story.append(img_final)

    story.append(Spacer(1, 0.55 * inch))
    story.append(Paragraph(datos["texto_final"], styles["TextoCentro"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(datos["unidad_final"], styles["TextoCentro"]))

    doc.build(story, onFirstPage=encabezado_pagina, onLaterPages=encabezado_pagina)

    try:
        os.remove(chart_path)
    except Exception:
        pass

    buffer_pdf.seek(0)
    return buffer_pdf


st.title("Generador de Informe Pareto Institucional")

st.markdown(
    """
    Herramienta para generar informes institucionales de análisis Pareto con tabla priorizada,
    gráfico y descarga en PDF.
    """
)

st.sidebar.header("Datos generales del informe")

titulo = st.sidebar.text_input("Título principal", "Informe de Resultados")

subtitulo = st.sidebar.text_input(
    "Subtítulo",
    "Análisis de Problemáticas Priorizadas en Seguridad Ciudadana"
)

tipo_pareto = st.sidebar.text_input("Tipo de informe", "Pareto General")

delegacion = st.sidebar.text_input("Delegación o región", "Delegación: D1-Carmen")

fecha_emision = st.sidebar.text_input(
    "Fecha de emisión",
    datetime.now().strftime("%d/%m/%Y")
)

programa = st.sidebar.text_input(
    "Programa",
    "Estrategia Integral de Prevención para la Seguridad Pública “Sembremos Seguridad”"
)

nota_tecnica = st.sidebar.text_area(
    "Nota técnica de portada",
    "Documento técnico generado a partir del procesamiento y priorización de datos obtenidos mediante encuestas."
)

introduccion_1 = st.sidebar.text_area(
    "Introducción - párrafo 1",
    "Este informe presenta los resultados del análisis de la información recopilada mediante encuestas, procesada a través de un enfoque metodológico que permite identificar, agrupar y priorizar las principales problemáticas en materia de seguridad ciudadana."
)

introduccion_2 = st.sidebar.text_area(
    "Introducción - párrafo 2",
    "En el marco de la Estrategia Integral de Prevención para la Seguridad Pública “Sembremos Seguridad”, los datos fueron tratados utilizando herramientas de análisis que permiten clasificar las variables según su relevancia y tipología."
)

texto_final = st.sidebar.text_area(
    "Texto página final",
    "Elaborado por la Estrategia Integral de Prevención para la Seguridad Pública “Sembremos Seguridad”."
)

unidad_final = st.sidebar.text_input(
    "Unidad final",
    "Dirección de Programas Policiales Preventivos – MSP"
)

st.subheader("1. Datos generales para el cálculo")

col1, col2 = st.columns(2)

with col1:
    total_general = st.number_input(
        "Total general de hechos",
        min_value=1,
        value=11710,
        step=1
    )

with col2:
    total_descriptores = st.number_input(
        "Total general de descriptores",
        min_value=1,
        value=88,
        step=1
    )

st.subheader("2. Ingreso de tabla priorizada")

col_limpia, col_aviso = st.columns([1, 3])

with col_limpia:
    limpiar_datos = st.button("Limpiar solo tabla y cálculos")

with col_aviso:
    st.caption("Este botón no borra la portada, introducción, nota técnica ni texto final. Solo limpia la tabla cargada.")

if limpiar_datos:
    st.session_state.tabla_texto_actual = TABLA_VACIA
    st.session_state.tabla_texto_widget = TABLA_VACIA
    st.session_state.datos_limpiados = True
    st.rerun()

if st.session_state.datos_limpiados:
    st.success("Datos de tabla limpiados. Los textos institucionales se mantienen.")

opcion = st.radio(
    "Seleccione la forma de ingreso",
    ["Pegar tabla", "Subir Excel o CSV"],
    horizontal=True,
    key="modo_ingreso"
)

df_base = pd.DataFrame(columns=["Descriptor priorizado", "Frecuencia"])

if opcion == "Pegar tabla":
    st.info("Copie desde Excel únicamente las columnas: Descriptor priorizado y Frecuencia.")

    tabla_texto = st.text_area(
        "Pegar tabla aquí",
        height=320,
        key="tabla_texto_widget"
    )

    st.session_state.tabla_texto_actual = tabla_texto

    df_base = leer_tabla_pegada(tabla_texto)

else:
    st.warning("Si desea limpiar un archivo cargado, presione el botón de limpieza y vuelva a cargar el archivo.")

    archivo = st.file_uploader("Subir archivo Excel o CSV", type=["xlsx", "csv"])

    if archivo is not None:
        if archivo.name.lower().endswith(".xlsx"):
            df_subido = pd.read_excel(archivo)
        else:
            df_subido = pd.read_csv(archivo)

        st.write("Vista previa del archivo cargado:")
        st.dataframe(df_subido.head(20), use_container_width=True)

        columnas = list(df_subido.columns)

        col_desc = st.selectbox("Columna de descriptor", columnas)
        col_freq = st.selectbox("Columna de frecuencia", columnas)

        df_base = df_subido[[col_desc, col_freq]].copy()
        df_base.columns = ["Descriptor priorizado", "Frecuencia"]

st.subheader("3. Editar tabla antes de generar el informe")

if df_base.empty:
    st.warning("Debe ingresar datos para continuar.")
    st.stop()

df_editado = st.data_editor(
    df_base,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Descriptor priorizado": st.column_config.TextColumn("Descriptor priorizado"),
        "Frecuencia": st.column_config.NumberColumn("Frecuencia", min_value=0, step=1),
    }
)

df = procesar_df(df_editado, total_general)

if df.empty:
    st.warning("La tabla no tiene datos válidos.")
    st.stop()

total_priorizado = int(df["Frecuencia"].sum())
cantidad_priorizados = len(df)

descriptor_top = df.iloc[0]["Descriptor priorizado"]
frecuencia_top = int(df.iloc[0]["Frecuencia"])
porcentaje_top = float(df.iloc[0]["Porcentaje"])
porcentaje_acumulado = float(df["Porcentaje acumulado"].iloc[-1])

texto_resultados_default = (
    f"Se registran {total_general} hechos distribuidos en {total_descriptores} descriptores. "
    f"El descriptor de mayor incidencia es {descriptor_top}, con {frecuencia_top} casos "
    f"({porcentaje_top:.2f}%). Para fines de priorización, se identificaron "
    f"{cantidad_priorizados} descriptores que concentran aproximadamente "
    f"{porcentaje_acumulado:.2f}% de los hechos."
)

st.subheader("4. Texto de resultados generales")

texto_resultados = st.text_area(
    "Puede editar este texto antes de generar el PDF",
    texto_resultados_default,
    height=130
)

st.subheader("5. Tabla procesada")

df_mostrar = df.copy()
df_mostrar["Porcentaje"] = df_mostrar["Porcentaje"].map(lambda x: f"{x:.2f}%")
df_mostrar["Porcentaje acumulado"] = df_mostrar["Porcentaje acumulado"].map(lambda x: f"{x:.2f}%")

st.dataframe(df_mostrar, use_container_width=True)

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Total priorizado", total_priorizado)
col_b.metric("Descriptores priorizados", cantidad_priorizados)
col_c.metric("Descriptor principal", descriptor_top)
col_d.metric("Porcentaje acumulado", f"{porcentaje_acumulado:.2f}%")

st.subheader("6. Gráfico Pareto priorizado")

chart_buffer_preview = crear_grafico_pareto(df)
st.image(chart_buffer_preview, use_container_width=True)

datos_pdf = {
    "titulo": titulo,
    "subtitulo": subtitulo,
    "tipo_pareto": tipo_pareto,
    "delegacion": delegacion,
    "fecha_emision": fecha_emision,
    "programa": programa,
    "nota_tecnica": nota_tecnica,
    "introduccion_1": introduccion_1,
    "introduccion_2": introduccion_2,
    "texto_final": texto_final,
    "unidad_final": unidad_final
}

st.subheader("7. Descargar informe")

pdf_buffer = generar_pdf(datos_pdf, df, texto_resultados)

nombre_delegacion = limpiar_nombre_archivo(delegacion)

if not nombre_delegacion:
    nombre_delegacion = "Sin nombre"

nombre_pdf = f"Pareto General Delegación {nombre_delegacion}.pdf"

st.download_button(
    label="Descargar PDF",
    data=pdf_buffer,
    file_name=nombre_pdf,
    mime="application/pdf"
)

excel_buffer = BytesIO()
df_exportar = df.copy()
df_exportar.to_excel(excel_buffer, index=False)
excel_buffer.seek(0)

nombre_excel = f"Tabla Pareto General Delegación {nombre_delegacion}.xlsx"

st.download_button(
    label="Descargar Excel procesado",
    data=excel_buffer,
    file_name=nombre_excel,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
