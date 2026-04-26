
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
Deficiencias en el alumbrado público\t147""",
        height=320
    )

    df_base = leer_tabla_pegada(tabla_texto)

else:
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
