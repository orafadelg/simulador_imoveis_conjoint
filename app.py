import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Simulador Conjoint - Empreendimentos", layout="wide")
st.title("🏗️ Simulador de Conjoint para Empreendimentos (Reativo)")
st.write("Ajuste as combinações e veja, em tempo real, o **SCORE de preferência**, a **intenção incremental** e o **custo** por opção.")

# Estilinho leve para separar visualmente os blocos
st.markdown("""
<style>
.card {
  border: 1px solid #e6e6e6;
  border-radius: 12px;
  padding: 14px 14px 8px 14px;
  background-color: #ffffff;
  box-shadow: 0 0 4px rgba(0,0,0,0.03);
}
.card h3 {
  margin-top: 0.2rem;
  margin-bottom: 0.6rem;
}
.section {
  border: 1px dashed #ddd;
  border-radius: 12px;
  padding: 12px;
  margin-top: 6px;
}
.metric-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# PARÂMETROS GERAIS (fictícios)
# -------------------------
BASE_INTENT = 0.30               # intenção base (30%)
INTENT_SCALE = 0.25              # quanto o 'score' afeta a intenção (escala)
UNIT_PRICE = 400_000             # preço médio unitário (R$)

# =========================
# COEFICIENTES (fictícios)
# =========================
impact_parede = {
    "Apenas cerâmica acima da bancada": -0.05,
    "Cerâmica do piso até 150cm": 0.08
}
impact_piso_sala_quarto = {
    "Sem piso": -0.12,
    "Piso laminado": 0.15
}
impact_bancadas = {
    "Louça + pia inox": -0.06,
    "Granito": 0.14
}
impact_itens_esportivos = {
    "Mini quadra recreativa": 0.05,
    "Piscina": 0.18
}
impact_itens_sociais_ind = {
    "Espaço pizza": 0.04,
    "Churrasqueira": 0.09
}
impact_facilites = {
    "Lavanderia": 0.06,
    "Pet care": 0.03
}

# Custos adicionais (R$ por unidade)
custo_parede = {"Apenas cerâmica acima da bancada": 0, "Cerâmica do piso até 150cm": 3_500}
custo_piso_sala_quarto = {"Sem piso": 0, "Piso laminado": 8_000}
custo_bancadas = {"Louça + pia inox": 0, "Granito": 6_500}
custo_itens_esportivos = {"Mini quadra recreativa": 15_000, "Piscina": 50_000}
custo_itens_sociais_ind = {"Espaço pizza": 4_000, "Churrasqueira": 12_000}
custo_facilites = {"Lavanderia": 5_000, "Pet care": 2_500}

# =========================
# AJUSTES POR SEGMENTO
# =========================
RENDA_OPCOES = ["4k-5k", "5k-6k", "6k-7k", "7k-8k"]
REGIAO_OPCOES = ["BH e RMBH", "SP e Interior", "RJ", "MG", "ES", "Sul", "NE", "CO/AM"]

mult_renda = {"4k-5k": 0.9, "5k-6k": 1.0, "6k-7k": 1.05, "7k-8k": 1.1}
mult_regiao = {"BH e RMBH": 1.0, "SP e Interior": 1.1, "RJ": 1.05, "MG": 0.98, "ES": 0.97, "Sul": 1.02, "NE": 0.95, "CO/AM": 0.93}

def avg_multiplier(selected, mapping, default=1.0):
    if not selected:
        return default
    return float(np.mean([mapping[s] for s in selected if s in mapping]))

# =========================
# SIDEBAR - FILTROS
# =========================
with st.sidebar:
    st.header("🎯 Filtros")
    renda_sel = st.multiselect("Faixa de renda", RENDA_OPCOES, default=["5k-6k"])
    regiao_sel = st.multiselect("Região do país", REGIAO_OPCOES, default=["SP e Interior"])

    renda_mult = avg_multiplier(renda_sel, mult_renda, default=1.0)
    regiao_mult = avg_multiplier(regiao_sel, mult_regiao, default=1.0)
    seg_mult = renda_mult * regiao_mult

    st.markdown("---")
    st.caption(f"Multiplicador de segmento (interno): **{seg_mult:.2f}**")

# =========================
# FUNÇÕES DE CÁLCULO
# =========================
def compute_score_and_cost(option_dict):
    score = (
        impact_parede[option_dict["Parede Hidráulica"]] +
        impact_piso_sala_quarto[option_dict["Piso Sala/Quarto"]] +
        impact_bancadas[option_dict["Bancadas"]] +
        impact_itens_esportivos[option_dict["Itens Esportivos"]] +
        impact_itens_sociais_ind[option_dict["Itens Sociais Individuais"]] +
        impact_facilites[option_dict["Facilites"]]
    )
    cost = (
        custo_parede[option_dict["Parede Hidráulica"]] +
        custo_piso_sala_quarto[option_dict["Piso Sala/Quarto"]] +
        custo_bancadas[option_dict["Bancadas"]] +
        custo_itens_esportivos[option_dict["Itens Esportivos"]] +
        custo_itens_sociais_ind[option_dict["Itens Sociais Individuais"]] +
        custo_facilites[option_dict["Facilites"]]
    )
    return score, cost

def summarize_option(name, option_dict, seg_mult):
    raw_score, add_cost = compute_score_and_cost(option_dict)
    adj_score = raw_score * seg_mult

    intent_uplift = adj_score * INTENT_SCALE          # variação absoluta 0–1
    intent_new = np.clip(BASE_INTENT + intent_uplift, 0, 1)

    revenue_add_per_unit = intent_uplift * UNIT_PRICE # aproximação
    per_unit_net = revenue_add_per_unit - add_cost

    return {
        "Opção": name,
        "SCORE PREFERENCIA": adj_score,
        "Intenção Base": BASE_INTENT,
        "Conversão (p.p.)": intent_uplift * 100,
        "Intenção Nova (%)": intent_new * 100,
        "Custo (R$)": add_cost,
        "Receita +/unid (R$)": revenue_add_per_unit,
        "Resultado Líquido +/unid (R$)": per_unit_net
    }

# =========================
# UI: 3 COLUNAS COM "CARDS"
# =========================
st.subheader("1) Três combinações (A, B e C)")

def option_card(name_key: str, title: str):
    st.markdown(f'<div class="card"><h3>{title}</h3>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        parede = st.selectbox("Parede Hidráulica", list(impact_parede.keys()), key=f"{name_key}_parede")
        piso = st.selectbox("Piso Sala/Quarto", list(impact_piso_sala_quarto.keys()), key=f"{name_key}_piso")
        bancada = st.selectbox("Bancadas", list(impact_bancadas.keys()), key=f"{name_key}_bancada")
    with c2:
        esportivo = st.selectbox("Itens Esportivos", list(impact_itens_esportivos.keys()), key=f"{name_key}_esportivo")
        social_ind = st.selectbox("Itens Sociais Individuais", list(impact_itens_sociais_ind.keys()), key=f"{name_key}_social")
        facil = st.selectbox("Facilites", list(impact_facilites.keys()), key=f"{name_key}_facil")

    option = {
        "Parede Hidráulica": parede,
        "Piso Sala/Quarto": piso,
        "Bancadas": bancada,
        "Itens Esportivos": esportivo,
        "Itens Sociais Individuais": social_ind,
        "Facilites": facil
    }
    summary = summarize_option(title.split()[-1], option, seg_mult)

    # Linha de métricas (3 colunas)
    m1, m2, m3 = st.columns(3)
    m1.metric("SCORE PREFERENCIA", f"{summary['SCORE PREFERENCIA']:.2f}")
    m2.metric("Conversão (p.p.)", f"{summary['Conversão (p.p.)']:.1f}")
    m3.metric("Custo (R$)", f"{summary['Custo (R$)']:,.0f}")

    # Linha complementar (receita e líquido) – deixa mais “executivo”
    m4, m5 = st.columns(2)
    m4.metric("Receita +/unid (R$)", f"{summary['Receita +/unid (R$)']:,.0f}")
    m5.metric("Resultado Líquido +/unid (R$)", f"{summary['Resultado Líquido +/unid (R$)']:,.0f}")

    st.markdown('</div>', unsafe_allow_html=True)
    return option, summary

colA, colB, colC = st.columns(3)
with colA:
    optA, sumA = option_card("A", "Combinação A")
with colB:
    optB, sumB = option_card("B", "Combinação B")
with colC:
    optC, sumC = option_card("C", "Combinação C")

# =========================
# RESULTADOS CONSOLIDADOS
# =========================
st.subheader("2) Comparativo consolidado")

results = [sumA, sumB, sumC]
df = pd.DataFrame(results)

# Ranking por Conversão incremental
rank_df = df.sort_values(by="Conversão (p.p.)", ascending=False)[["Opção", "Conversão (p.p.)"]]
chart_rank = alt.Chart(rank_df).mark_bar().encode(
    x=alt.X("Conversão (p.p.):Q", title="Uplift de Intenção (pontos percentuais)"),
    y=alt.Y("Opção:N", sort="-x"),
    tooltip=["Opção", "Conversão (p.p.)"]
).properties(title="Ranking por Uplift de Intenção", height=220)
st.altair_chart(chart_rank, use_container_width=True)

# Tabela “executiva”
st.markdown("**Tabela resumida (por opção):**")
cols_order = [
    "Opção", "SCORE PREFERENCIA", "Intenção Base", "Conversão (p.p.)",
    "Intenção Nova (%)", "Custo (R$)", "Receita +/unid (R$)", "Resultado Líquido +/unid (R$)"
]
st.dataframe(
    df[cols_order].style.format({
        "SCORE PREFERENCIA": "{:.2f}",
        "Intenção Base": "{:.0%}",
        "Conversão (p.p.)": "{:.1f}",
        "Intenção Nova (%)": "{:.0f}%",
        "Custo (R$)": "R$ {:,.0f}",
        "Receita +/unid (R$)": "R$ {:,.0f}",
        "Resultado Líquido +/unid (R$)": "R$ {:,.0f}"
    }),
    use_container_width=True
)

# Custo vs Receita adicional (por unidade)
st.subheader("3) Custo x Receita Adicional (por Unidade)")
comp_df = df[["Opção", "Custo (R$)", "Receita +/unid (R$)", "Resultado Líquido +/unid (R$)"]]
cost_rev_df = comp_df.melt(
    id_vars=["Opção"],
    value_vars=["Custo (R$)", "Receita +/unid (R$)"],
    var_name="Métrica",
    value_name="Valor (R$)"
)
chart_cost_rev = alt.Chart(cost_rev_df).mark_bar().encode(
    x=alt.X("Opção:N"),
    y=alt.Y("Valor (R$):Q"),
    color="Métrica:N",
    tooltip=["Opção", "Métrica", "Valor (R$)"]
).properties(title="Custo vs Receita adicional")
st.altair_chart(chart_cost_rev, use_container_width=True)

st.caption("Números fictícios para demonstração. Substitua por coeficientes/custos reais quando disponíveis.")
