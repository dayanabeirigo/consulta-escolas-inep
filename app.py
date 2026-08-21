import glob
import re
import os
import pandas as pd
import streamlit as st
from unidecode import unidecode

st.set_page_config(
    page_title="Consulta de Escolas - Censo Escolar 2025",
    layout="wide",
    page_icon="🔍",
)

st.title("🔍 Consulta de Escolas (Pública / Privada)")
st.write("Base de dados: Microdados do Censo Escolar 2025 (INEP / EducaMundo)")


# Função para normalizar textos (remove acentos, símbolos e põe em caixa baixa)
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = unidecode(texto.lower())
    texto = re.sub(r"[^\w\s]", "", texto)  # Remove pontuações
    return texto.strip()


@st.cache_data
def carregar_dados():
    arquivos_csv = glob.glob("**/*.csv", recursive=True)
    arquivos_zip = glob.glob("**/*.zip", recursive=True)
    todos_arquivos = arquivos_csv + arquivos_zip

    caminho_arquivo = None
    for arq in todos_arquivos:
        if "escola" in arq.lower() or "entidade" in arq.lower():
            caminho_arquivo = arq
            break

    if not caminho_arquivo and todos_arquivos:
        caminho_arquivo = todos_arquivos[0]

    if not caminho_arquivo:
        raise FileNotFoundError(
            "Nenhum arquivo de dados (.csv ou .zip) foi encontrado no repositório."
        )

    colunas_necessarias = [
        "CO_ENTIDADE",
        "NO_ENTIDADE",
        "SG_UF",
        "NO_MUNICIPIO",
        "TP_DEPENDENCIA",
    ]

    df = pd.read_csv(
        caminho_arquivo,
        sep=";",
        encoding="iso-8859-1",
        usecols=colunas_necessarias,
        low_memory=False,
    )

    mapa_dependencia = {
        1: "Pública (Federal)",
        2: "Pública (Estadual)",
        3: "Pública (Municipal)",
        4: "Privada",
    }
    df["TIPO_DEPENDENCIA"] = df["TP_DEPENDENCIA"].map(mapa_dependencia)

    df = df.rename(
        columns={
            "CO_ENTIDADE": "Código INEP",
            "NO_ENTIDADE": "Nome da Escola",
            "SG_UF": "UF",
            "NO_MUNICIPIO": "Município",
            "TIPO_DEPENDENCIA": "Dependência Administrativa",
        }
    )

    # Coluna auxiliar otimizada para busca aproximada/flexível
    df["NOME_NORMALIZADO"] = df["Nome da Escola"].apply(normalizar_texto)

    return df


try:
    with st.spinner("Carregando base de dados das escolas..."):
        df_base = carregar_dados()

    # --- BARRA LATERAL / FILTROS PRELIMINARES ---
    st.sidebar.header("📌 Filtros de Localização")

    # Filtro de Estado (UF)
    estados = ["Todos"] + sorted(df_base["UF"].dropna().unique().tolist())
    uf_selecionada = st.sidebar.selectbox("Selecione o Estado (UF):", estados)

    if uf_selecionada != "Todos":
        df_filtrado = df_base[df_base["UF"] == uf_selecionada]
    else:
        df_filtrado = df_base

    # Filtro de Município
    municipios = ["Todos"] + sorted(
        df_filtrado["Município"].dropna().unique().tolist()
    )
    municipio_selecionado = st.sidebar.selectbox(
        "Selecione o Município:", municipios
    )

    if municipio_selecionado != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["Município"] == municipio_selecionado
        ]

    # --- IDENTIFICAÇÃO DA DESENVOLVEDORA ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛠️ Créditos")
    st.sidebar.write(
        "**Desenvolvido por:**\nDayana Cecília Reis Beirigo Dutra"
    )
    st.sidebar.caption("Sistema desenvolvido para apoio às comissões.")

    # --- CAMPO DE BUSCA PRINCIPAL ---
    busca = st.text_input(
        "Digite o Nome da Escola (ou termos aproximados / Código INEP) e aperte Enter:"
    )

    if busca:
        busca_normalizada = normalizar_texto(busca)
        palavras_chave = busca_normalizada.split()

        # Verifica se o termo digitado é um número (Código INEP)
        if busca.strip().isdigit():
            resultado = df_filtrado[
                df_filtrado["Código INEP"].astype(str).str.contains(busca.strip(), na=False)
            ]
        else:
            # Filtro aproximado: busca registros que contenham TODAS as palavras digitadas, independente da ordem ou acentos
            mascara = pd.Series([True] * len(df_filtrado), index=df_filtrado.index)
            for palavra in palavras_chave:
                mascara = mascara & df_filtrado["NOME_NORMALIZADO"].str.contains(
                    palavra, na=False
                )

            resultado = df_filtrado[mascara]
    else:
        resultado = df_filtrado

    # --- EXIBIÇÃO DOS RESULTADOS ---
    if busca or uf_selecionada != "Todos" or municipio_selecionado != "Todos":
        if not resultado.empty:
            st.success(f"Encontrado(s) {len(resultado)} registro(s):")
            st.dataframe(
                resultado[
                    [
                        "Código INEP",
                        "Nome da Escola",
                        "UF",
                        "Município",
                        "Dependência Administrativa",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("Nenhuma escola encontrada com os termos/filtros selecionados.")
    else:
        st.info(
            "💡 Utilize a barra lateral para filtrar por Estado/Município ou digite o nome/código na caixa acima."
        )

except Exception as e:
    st.error(f"Erro ao carregar os dados. Detalhes: {e}")
