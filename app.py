import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(layout="wide")

st.title("Simulador de Conjoint para Medicamentos TDAH")
st.caption("Comparação reativa de 3 combinações com cálculo automático de preferência, probabilidade de escolha, intenção incremental e custo incremental.")

# ------------------------------
# 1) MODELO (coeficientes fictícios do estudo)
# ------------------------------
marca_impact = {'Genérico': -0.20, 'Atenta': 0.10, 'Juneve': 0.15, 'Venvanse': 0.30}
dosagem_impact = {'30mg': -0.10, '50mg': 0.00, '70mg': 0.20}
preco_impact = {'R$100': 0.20, 'R$150': 0.00, 'R$200': -0.20}
quantidade_impact = {'30 comprimidos': -0.10, '60 comprimidos': 0.10}

# utilidade total = soma dos impactos (modelo aditivo simples)

def parse_preco(preco_str: str) -> float:
    return float(preco_str.replace('R$', '').replace('.', '').strip())

def parse_qtd(qtd_str: str) -> int:
    return int(qtd_str.split()[0])

def utilidade(marca, dose, preco, qtd):
    return (
        marca_impact[marca]
        + dosagem_impact[dose]
        + preco_impact[preco]
        + quantidade_impact[qtd]
    )

# ------------------------------
# 2) ENTRADAS DO USUÁRIO
# ------------------------------
colA, colB, colC = st.columns(3)

with colA:
    st.subheader("Opção A")
    a_marca = st.selectbox("Marca", list(marca_impact.keys()), key="a_marca")
    a_dose = st.selectbox("Dosagem", list(dosagem_impact.keys()), key="a_dose")
    a_preco = st.selectbox("Preço", list(preco_impact.keys()), key="a_preco")
    a_qtd = st.selectbox("Quantidade", list(quantidade_impact.keys()), key="a_qtd")

with colB:
    st.subheader("Opção B")
    b_marca = st.selectbox("Marca", list(marca_impact.keys()), key="b_marca")
    b_dose = st.selectbox("Dosagem", list(dosagem_impact.keys()), key="b_dose")
    b_preco = st.selectbox("Preço", list(preco_impact.keys()), key="b_preco")
    b_qtd = st.selectbox("Quantidade", list(quantidade_impact.keys()), key="b_qtd")

with colC:
    st.subheader("Opção C")
    c_marca = st.selectbox("Marca", list(marca_impact.keys()), key="c_marca")
    c_dose = st.selectbox("Dosagem", list(dosagem_impact.keys()), key="c_dose")
    c_preco = st.selectbox("Preço", list(preco_impact.keys()), key="c_preco")
    c_qtd = st.selectbox("Quantidade", list(quantidade_impact.keys()), key="c_qtd")

# ------------------------------
# 3) CÁLCULO REATIVO – PREFERÊNCIA E PROBABILIDADE
# ------------------------------
U_A = utilidade(a_marca, a_dose, a_preco, a_qtd)
U_B = utilidade(b_marca, b_dose, b_preco, b_qtd)
U_C = utilidade(c_marca, c_dose, c_preco, c_qtd)

# Softmax p/ converter utilidade em probabilidade de escolha
expA, expB, expC = np.exp([U_A, U_B, U_C])
sumexp = expA + expB + expC
P_A, P_B, P_C = expA / sumexp, expB / sumexp, expC / sumexp

# ------------------------------
# 4) CUSTO E INTENÇÃO INCREMENTAL (base selecionável)
# ------------------------------
base = st.radio(
    "Escolha a base para cálculo incremental:",
    options=["A", "B", "C"],
    horizontal=True,
)

preco_num = {
    "A": parse_preco(a_preco),
    "B": parse_preco(b_preco),
    "C": parse_preco(c_preco),
}
qtd_num = {
    "A": parse_qtd(a_qtd),
    "B": parse_qtd(b_qtd),
    "C": parse_qtd(c_qtd),
}
prob = {"A": P_A, "B": P_B, "C": P_C}
score = {"A": U_A, "B": U_B, "C": U_C}

# custo por comprimido
custo_unit = {k: (preco_num[k] / qtd_num[k]) for k in ["A", "B", "C"]}

# deltas vs base
inc_prob = {k: (prob[k] - prob[base]) for k in ["A", "B", "C"]}
inc_custo_pack = {k: (preco_num[k] - preco_num[base]) for k in ["A", "B", "C"]}
inc_custo_unit = {k: (custo_unit[k] - custo_unit[base]) for k in ["A", "B", "C"]}

# ------------------------------
# 5) EXIBIÇÃO EM 3 COLUNAS – SCORES E INCREMENTAIS
# ------------------------------
col1, col2, col3 = st.columns(3)

def bloco_resultados(col, label):
    with col:
        st.markdown(f"### {label}")
        st.markdown(f"**SCORE PREFERÊNCIA:** {score[label]:.3f}")
        st.markmarkdown = st.markdown  # alias para legibilidade
        st.markdown(f"**Prob. Estimada:** {prob[label]*100:.1f}%")
        st.markdown("—")
        st.markdown(f"**Intenção incremental (vs {base}):** {inc_prob[label]*100:.1f} pp")
        st.markdown(f"**Custo incremental por pack (vs {base}):** R${inc_custo_pack[label]:.2f}")
        st.markdown(f"**Custo incremental por comprimido (vs {base}):** R${inc_custo_unit[label]:.2f}")

bloco_resultados(col1, "A")
bloco_resultados(col2, "B")
bloco_resultados(col3, "C")

# ------------------------------
# 6) VISUALIZAÇÃO – BARRAS DE PROBABILIDADE
# ------------------------------
vis_df = pd.DataFrame({
    "Opção": ["A", "B", "C"],
    "Probabilidade": [P_A, P_B, P_C],
    "Score": [U_A, U_B, U_C],
})

bars = (
    alt.Chart(vis_df)
    .mark_bar()
    .encode(x=alt.X("Opção:N"), y=alt.Y("Probabilidade:Q", axis=alt.Axis(format="%")), color="Opção:N")
    .properties(title="Probabilidade Estimada de Escolha (softmax)")
)
labels = (
    alt.Chart(vis_df)
    .mark_text(dy=-5)
    .encode(x="Opção:N", y="Probabilidade:Q", text=alt.Text("Probabilidade:Q", format=".0%"))
)

st.altair_chart(bars + labels, use_container_width=True)

# ------------------------------
# 7) PREÇO IDEAL – CURVA SIMULADA E PONTO ÓTIMO
# ------------------------------
# Curva simplificada: demanda decresce linearmente com preço (exemplo)
precos = np.arange(80, 241, 10)
# demanda baseada em uma reta: 100% em R$80 e 10% em R$240 (apenas exemplo)
demanda = np.clip(1.2 - (precos / 200), 0.1, 1.0)
# Receita por pack (demanda * preço)
receita = demanda * precos
curva_df = pd.DataFrame({"Preço (R$)": precos, "Demanda Estimada": demanda, "Receita": receita})

# ponto de máxima receita
idx_opt = int(np.argmax(receita))
preco_opt = precos[idx_opt]

demanda_chart = (
    alt.Chart(curva_df)
    .transform_fold(["Demanda Estimada", "Receita"], as_=["Métrica", "Valor"]) 
    .mark_line(point=True)
    .encode(x="Preço (R$):Q", y="Valor:Q", color="Métrica:N")
    .properties(title=f"Curva de Preço Ideal (ponto ótimo ≈ R${preco_opt})")
)

st.subheader("Curva de Preço Ideal (Simulada)")
st.altair_chart(demanda_chart, use_container_width=True)

st.caption("Notas: coeficientes e curvas são ilustrativos para demonstração. Em projeto real, estimamos utilidades via modelos (ex.: Logit, HB) e a curva de preço ideal via PSM/Gabor-Granger/Conjoint.")
