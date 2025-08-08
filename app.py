import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Simulador Conjoint - Empreendimentos", layout="wide")
st.title("🏗️ Simulador de Conjoint para Empreendimentos")
st.write("Compare três combinações de atributos e veja impacto estimado em intenção de compra vs. custo adicional (valores fictícios).")

# -------------------------
# PARÂMETROS (ajuste livre)
# -------------------------
BASE_INTENT = 0.30               # intenção base (30%)
INTENT_SCALE = 0.25              # quanto o 'score' afeta a intenção (escala)
UNIT_PRICE = 400_000             # preço médio unitário (R$)
COHORT_UNITS = 100               # tamanho de coorte para cálculo agregado

# =========================
# COEFICIENTES (fictícios)
# =========================
# Impactos parciais (como utilidades) por nível de atributo
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

# Custos adicionais (fictícios) por nível de atributo (R$ por unidade)
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

# Multiplicadores (fictícios) que afetam a sensibilidade aos atributos (impact score)
# Pode interpretar como "quanto aquele segmento valoriza upgrades".
mult_renda = {
    "4k-5k": 0.9,
    "5k-6k": 1.0,
    "6k-7k": 1.05,
    "7k-8k": 1.1
}
mult_regiao = {
    "BH e RMBH": 1.0,
    "SP e Interior": 1.1,
    "RJ": 1.05,
    "MG": 0.98,
    "ES": 0.97,
    "Sul": 1.02,
    "NE": 0.95,
    "CO/AM": 0.93
}

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
# UI: Seleção das 3 opções
# =========================
st.subheader("1) Selecione as combinações A, B e C")

def option_form(prefix: str):
    c1, c2, c3 = st.columns(3)
    with c1:
        parede = st.selectbox(f"{prefix} - Parede Hidráulica", list(impact_parede.keys()), key=f"{prefix}_parede")
        piso = st.selectbox(f"{prefix} - Piso Sala/Quarto", list(impact_piso_sala_quarto.keys()), key=f"{prefix}_piso")
    with c2:
        bancada = st.selectbox(f"{prefix} - Bancadas", list(impact_bancadas.keys()), key=f"{prefix}_bancada")
        esportivo = st.selectbox(f"{prefix} - Itens Esportivos", list(impact_itens_esportivos.keys()), key=f"{prefix}_esportivo")
    with c3:
        social_ind = st.selectbox(f"{prefix} - Itens Sociais Individuais", list(impact_itens_sociais_ind.keys()), key=f"{prefix}_social")
        facil = st.selectbox(f"{prefix} - Facilites", list(impact_facilites.keys()), key=f"{prefix}_facil")
    return {
        "Parede Hidráulica": parede,
        "Piso Sala/Quarto": piso,
        "Bancadas": bancada,
        "Itens Esportivos": esportivo,
        "Itens Sociais Individuais": social_ind,
        "Facilites": facil
    }

optA = option_form("Opção A")
optB = option_form("Opção B")
optC = option_form("Opção C")

# =========================
# CÁLCULOS
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

    # Ajuste por segmento e conversão p/ intenção
    adj_score = raw_score * seg_mult
    intent_uplift = adj_score * INTENT_SCALE  # variação absoluta (ex.: +0.20 = +20 p.p.)
    intent_new = np.clip(BASE_INTENT + intent_uplift, 0, 1)

    # Receita adicional por unidade (aproximação): uplift * preço médio
    revenue_add_per_unit = intent_uplift * UNIT_PRICE

    # Comparação simples (unitária e coorte)
    per_unit_net = revenue_add_per_unit - add_cost
    cohort_revenue_add = revenue_add_per_unit * COHORT_UNITS
    cohort_cost_add = add_cost * COHORT_UNITS
    cohort_net = cohort_revenue_add - cohort_cost_add

    return {
        "Opção": name,
        "Score (ajustado)": adj_score,
        "Intenção Base": BASE_INTENT,
        "Intenção Nova": intent_new,
        "Uplift de Intenção (p.p.)": intent_uplift * 100,
        "Custo Adicional (R$)": add_cost,
        "Receita Adicional / Unidade (R$)": revenue_add_per_unit,
        "Resultado Líquido / Unidade (R$)": per_unit_net,
        f"Receita Adicional / {COHORT_UNITS} und (R$)": cohort_revenue_add,
        f"Custo Adicional / {COHORT_UNITS} und (R$)": cohort_cost_add,
        f"Resultado Líquido / {COHORT_UNITS} und (R$)": cohort_net
    }

if st.button("Calcular Preferências e Impactos"):
    results = [
        summarize_option("A", optA, seg_mult),
        summarize_option("B", optB, seg_mult),
        summarize_option("C", optC, seg_mult),
    ]
    df = pd.DataFrame(results)

    # =========================
    # 2) RANKING / VISUALIZAÇÕES
    # =========================
    st.subheader("2) Ranking de Preferências (por Uplift de Intenção)")
    rank_df = df.sort_values(by="Uplift de Intenção (p.p.)", ascending=False)[["Opção", "Uplift de Intenção (p.p.)"]]
    chart_rank = alt.Chart(rank_df).mark_bar().encode(
        x=alt.X("Uplift de Intenção (p.p.):Q", title="Uplift de Intenção (pontos percentuais)"),
        y=alt.Y("Opção:N", sort="-x"),
        tooltip=["Opção", "Uplift de Intenção (p.p.)"]
    ).properties(height=200)
    st.altair_chart(chart_rank, use_container_width=True)

    st.markdown("**Tabela Detalhada (por opção):**")
    st.dataframe(df.style.format({
        "Score (ajustado)": "{:.2f}",
        "Intenção Base": "{:.0%}",
        "Intenção Nova": "{:.0%}",
        "Uplift de Intenção (p.p.)": "{:.1f}",
        "Custo Adicional (R$)": "R$ {:,.0f}",
        "Receita Adicional / Unidade (R$)": "R$ {:,.0f}",
        "Resultado Líquido / Unidade (R$)": "R$ {:,.0f}",
        f"Receita Adicional / {COHORT_UNITS} und (R$)": "R$ {:,.0f}",
        f"Custo Adicional / {COHORT_UNITS} und (R$)": "R$ {:,.0f}",
        f"Resultado Líquido / {COHORT_UNITS} und (R$)": "R$ {:,.0f}",
    }), use_container_width=True)

    # =========================
    # 3) COMPARAÇÃO CUSTO x INTENÇÃO
    # =========================
    st.subheader("3) Custo x Intenção (por Unidade)")
    comp_df = df[["Opção", "Uplift de Intenção (p.p.)", "Custo Adicional (R$)", "Receita Adicional / Unidade (R$)", "Resultado Líquido / Unidade (R$)"]]

    c1, c2 = st.columns(2)
    with c1:
        chart_uplift = alt.Chart(comp_df).mark_bar().encode(
            x=alt.X("Opção:N"),
            y=alt.Y("Uplift de Intenção (p.p.):Q"),
            tooltip=["Opção", "Uplift de Intenção (p.p.)"]
        ).properties(title="Uplift de Intenção (p.p.)")
        st.altair_chart(chart_uplift, use_container_width=True)

    with c2:
        cost_rev_df = comp_df.melt(id_vars=["Opção"], value_vars=["Custo Adicional (R$)", "Receita Adicional / Unidade (R$)"],
                                   var_name="Métrica", value_name="Valor (R$)")
        chart_cost_rev = alt.Chart(cost_rev_df).mark_bar().encode(
            x=alt.X("Opção:N"),
            y=alt.Y("Valor (R$):Q"),
            color="Métrica:N",
            tooltip=["Opção", "Métrica", "Valor (R$)"]
        ).properties(title="Custo vs Receita Adicional (por unidade)")
        st.altair_chart(chart_cost_rev, use_container_width=True)

    st.info(
        "Exemplo interpretativo: uma combinação pode **aumentar o custo em ~R$ 34.000 por unidade**, "
        "mas gerar **receita adicional estimada de ~R$ 78.000 por unidade** (via maior intenção de compra), "
        "resultando em **resultado líquido positivo**."
    )

# =========================
# 4) Curva de Preço (opcional/fictícia)
# =========================
st.subheader("4) Curva de Preço Ideal (Simulada)")
precos = [300_000, 340_000, 380_000, 420_000, 460_000, 500_000]
demanda = [95, 88, 76, 60, 45, 30]  # % demanda relativa fictícia
curva_df = pd.DataFrame({"Preço (R$)": precos, "Demanda Estimada (%)": demanda})
curva_chart = alt.Chart(curva_df).mark_line(point=True).encode(
    x=alt.X("Preço (R$):Q"),
    y=alt.Y("Demanda Estimada (%):Q"),
    tooltip=["Preço (R$)", "Demanda Estimada (%)"]
).properties(title="Curva de Demanda x Preço")
st.altair_chart(curva_chart, use_container_width=True)

st.caption("Coeficientes, custos e curva são fictícios para ilustração. Plugue dados reais quando disponíveis.")
