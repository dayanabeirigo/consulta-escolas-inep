import os
import re
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


def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = unidecode(texto.lower())
    texto = re.sub(r"[^\w\s]", " ", texto)
    return " ".join(texto.split())


@st.cache_data
def carregar_dados():
    caminho_base = "escolas_censo_2025.csv"

    if not os.path.exists(caminho_base):
        import glob

        arquivos = glob.glob("**/*escolas_censo_2025*.csv", recursive=True)
        if arquivos:
            caminho_base = arquivos[0]
        else:
            raise FileNotFoundError(
                "O arquivo 'escolas_censo_2025.csv' não foi encontrado no GitHub."
            )

    df = pd.read_csv(
        caminho_base,
        sep=";",
        encoding="iso-8859-1",
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

    df["NOME_NORMALIZADO"] = df["Nome da Escola"].apply(normalizar_texto)
    return df


try:
    with st.spinner("Carregando base de dados das escolas..."):
        df_base = carregar_dados()

    # --- BARRA LATERAL / FILTROS ---
    st.sidebar.header("📌 Filtros de Localização")

    estados = ["Todos"] + sorted(df_base["UF"].dropna().unique().tolist())
    uf_selecionada = st.sidebar.selectbox("Selecione o Estado (UF):", estados)

    if uf_selecionada != "Todos":
        df_filtrado = df_base[df_base["UF"] == uf_selecionada]
    else:
        df_filtrado = df_base

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

    # --- CRÉDITOS ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛠️ Créditos")
    st.sidebar.write(
        "**Desenvolvido por:**\nDayana Cecília Reis Beirigo Dutra"
    )
    st.sidebar.caption("Sistema desenvolvido para apoio às comissões.")

    # --- CAMPO DE BUSCA ---
    busca = st.text_input(
        "Digite o Nome da Escola (ex: Caetano Azeredo) ou Código INEP e aperte Enter:"
    )

    if busca:
        busca_limpa = busca.strip()

        if busca_limpa.isdigit():
            resultado = df_filtrado[
                df_filtrado["Código INEP"]
                .astype(str)
                .str.contains(busca_limpa, na=False)
            ]
        else:
            palavras = normalizar_texto(busca_limpa).split()
            palavras_filtradas = [
                p
                for p in palavras
                if p not in ["escola", "colegio", "estadual", "municipal"]
            ]
            if not palavras_filtradas:
                palavras_filtradas = palavras

            mascara = pd.Series(
                [True] * len(df_filtrado), index=df_filtrado.index
            )
            for palavra in palavras_filtradas:
                mascara = mascara & df_filtrado["NOME_NORMALIZADO"].str.contains(
                    re.escape(palavra), na=False
                )

            resultado = df_filtrado[mascara]
    else:
        resultado = pd.DataFrame()

    # --- EXIBIÇÃO ---
    if busca:
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
            st.warning(
                "Nenhuma escola encontrada. Tente buscar apenas o nome principal (ex: 'Caetano Azeredo')."
            )
    else:
        st.info(
            "💡 Digite o nome da escola ou o código INEP na caixa de pesquisa para iniciar a consulta."
        )

except Exception as e:
    st.error(f"Erro ao carregar os dados. Detalhes: {e}")
