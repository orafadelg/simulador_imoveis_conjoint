import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Simulador Conjoint - Empreendimentos", layout="wide")
st.title("🏗️ Simulador de Conjoint para Empreendimentos (Reativo)")
st.write("Ajuste as combinações e veja, em tempo real, o SCORE de preferência, a intenção incremental e o custo incremental por opção.")

# -------------------------
# PARÂMETROS GERAIS (fictícios)
# -------------------------
BASE_INTENT = 0.30               # intenção base (30%)
INTENT_SCALE = 0.25              # quanto o 'score' afeta a intenção (escala)
UNIT_PRICE = 400_000             # preço médio unitário (R$)
COHORT_UNITS = 100               # coorte para cálculos agregados

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
custo_parede = {
    "Apenas cerâmica acima da bancada": 0,
    "Cerâmica do piso até 150cm": 3_500
}
custo_piso_sala_quarto = {
    "Sem piso": 0,
    "Piso laminado": 8_000
}
custo_bancadas = {
    "Louça + pia inox": 0,
    "Granito": 6_500
}
custo_itens_esportivos = {
    "Mini quadra recreativa": 15_000,
    "Piscina": 50_000
}
custo_itens_sociais_ind = {
    "Espaço pizza": 4_000,
    "Churrasqueira": 12_000
}
custo_facilites = {
    "Lavanderia": 5_000,
    "Pet care": 2_500
}

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

    intent_uplift = adj_score * INTENT_SCALE          # variação absoluta da intenção (0.00–1.00)
    intent_new = np.clip(BASE_INTENT + intent_uplift, 0, 1)

    revenue_add_per_unit = intent_uplift * UNIT_PRICE # aproximação
    per_unit_net = revenue_add_per_unit - add_cost

    return {
        "Opção": name,
        "SCORE PREFERENCIA": adj_score,
        "Intenção Base": BASE_INTENT,
        "Conversão (Intenção incremental, p.p.)": intent_uplift * 100,
        "Intenção Nova (%)": intent_new * 100,
        "Custo (R$)": add_cost,
        "Receita Adicional / Unidade (R$)": revenue_add_per_unit,
        "Resultado Líquido / Unidade (R$)": per_unit_net
    }

# =========================
# UI: 3 COLUNAS DE COMBINAÇÕES
# =========================
st.subheader("1) Três combinações (A, B e C)")

def option_form(prefix: str):
    st.markdown(f"### **{prefix}**")
    c1, c2 = st.columns(2)
    with c1:
        parede = st.selectbox(f"{prefix} - Parede Hidráulica", list(impact_parede.keys()), key=f"{prefix}_parede")
        piso = st.selectbox(f"{prefix} - Piso Sala/Quarto", list(impact_piso_sala_quarto.keys()), key=f"{prefix}_piso")
        bancada = st.selectbox(f"{prefix} - Bancadas", list(impact_bancadas.keys()), key=f"{prefix}_bancada")
    with c2:
        esportivo = st.selectbox(f"{prefix} - Itens Esportivos", list(impact_itens_esportivos.keys()), key=f"{prefix}_esportivo")
        social_ind = st.selectbox(f"{prefix} - Itens Sociais Individuais", list(impact_itens_sociais_ind.keys()), key=f"{prefix}_social")
        facil = st.selectbox(f"{prefix} - Facilites", list(impact_facilites.keys()), key=f"{prefix}_facil")

    option = {
        "Parede Hidráulica": parede,
        "Piso Sala/Quarto": piso,
        "Bancadas": bancada,
        "Itens Esportivos": esportivo,
        "Itens Sociais Individuais": social_ind,
        "Facilites": facil
    }

    # Cálculo reativo
    summary = summarize_option(prefix[-1], option, seg_mult)

    # Métricas logo abaixo
    m1, m2, m3 = st.columns(3)
    m1.metric("SCORE PREFERENCIA", f"{summary['SCORE PREFERENCIA']:.2f}")
    m2.metric("Conversão (p.p.)", f"{summary['Conversão (Intenção incremental, p.p.)']:.1f}")
    m3.metric("Custo (R$)", f"{summary['Custo (R$)']:,.0f}")

    return option, summary

colA, colB, colC = st.columns(3)
with colA:
    optA, sumA = option_form("Opção A")
with colB:
    optB, sumB = option_form("Opção B")
with colC:
    optC, sumC = option_form("Opção C")

# =========================
# TABELA + VISUALIZAÇÕES (reativas)
# =========================
results = [sumA, sumB, sumC]
df = pd.DataFrame(results)

st.subheader("2) Ranking de Preferências (por Conversão incremental)")
rank_df = df.sort_values(by="Conversão (Intenção incremental, p.p.)", ascending=False)[["Opção", "Conversão (Intenção incremental, p.p.)"]]
chart_rank = alt.Chart(rank_df).mark_bar().encode(
    x=alt.X("Conversão (Intenção incremental, p.p.):Q", title="Uplift de Intenção (pontos percentuais)"),
    y=alt.Y("Opção:N", sort="-x"),
    tooltip=["Opção", "Conversão (Intenção incremental, p.p.)"]
).properties(height=200)
st.altair_chart(chart_rank, use_container_width=True)

st.markdown("**Tabela Detalhada (por opção):**")
st.dataframe(
    df[[
        "Opção",
        "SCORE PREFERENCIA",
        "Intenção Base",
        "Conversão (Intenção incremental, p.p.)",
        "Intenção Nova (%)",
        "Custo (R$)",
        "Receita Adicional / Unidade (R$)",
        "Resultado Líquido / Unidade (R$)"
    ]].style.format({
        "SCORE PREFERENCIA": "{:.2f}",
        "Intenção Base": "{:.0%}",
        "Conversão (Intenção incremental, p.p.)": "{:.1f}",
        "Intenção Nova (%)": "{:.0f}%",
        "Custo (R$)": "R$ {:,.0f}",
        "Receita Adicional / Unidade (R$)": "R$ {:,.0f}",
        "Resultado Líquido / Unidade (R$)": "R$ {:,.0f}"
    }),
    use_container_width=True
)

st.subheader("3) Custo x Receita Adicional (por Unidade)")
comp_df = df[["Opção", "Custo (R$)", "Receita Adicional / Unidade (R$)", "Resultado Líquido / Unidade (R$)"]]
cost_rev_df = comp_df.melt_
