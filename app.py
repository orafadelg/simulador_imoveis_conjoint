import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Simulador Conjoint - Empreendimentos (A/B)", layout="wide")
st.title("🏗️ Simulador de Conjoint para Empreendimentos (A/B)")
st.write("Ajuste as combinações A e B e veja, em tempo real, o **SCORE de preferência**, a **intenção incremental** e o **custo**, com destaque de vencedor diretamente nos cards.")

# =========================
# ESTILO (cards + métricas coloridas)
# =========================
st.markdown("""
<style>
.card {
  border: 1px solid #e6e6e6; border-radius: 12px; padding: 14px;
  background-color: #fff; box-shadow: 0 0 4px rgba(0,0,0,0.03);
}
.metric-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 8px;
}
.metric-grid-2 {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 8px;
}
.metric-box {
  border: 1px solid #eee; border-radius: 10px; padding: 10px;
  background: #fafafa;
}
.metric-label { font-size: 12px; color: #666; margin-bottom: 2px; }
.metric-value { font-size: 18px; font-weight: 700; }
.win .metric-value { color: #0f7b0f; }   /* verde vencedor */
.lose .metric-value { color: #9b1c1c; }  /* vermelho perdedor */
.tie  .metric-value { color: #444; }     /* empate/neutro */
</style>
""", unsafe_allow_html=True)

# =========================
# PARÂMETROS GERAIS (fictícios)
# =========================
BASE_INTENT = 0.30        # intenção base (30%)
INTENT_SCALE = 0.25       # quanto o score afeta a intenção
UNIT_PRICE = 400_000      # preço médio unitário (R$)

# Regra de "maior é melhor" por métrica (apenas Custo é menor-melhor)
HIGHER_BETTER = {
    "SCORE PREFERENCIA": True,
    "Conversão (p.p.)": True,
    "Intenção Nova (%)": True,
    "Custo (R$)": False,  # único invertido
    "Receita +/unid (R$)": True,
    "Resultado Líquido +/unid (R$)": True
}

# =========================
# COEFICIENTES (fictícios)
# =========================
impact_parede = {
    "Apenas cerâmica acima da bancada": -0.05,
    "Cerâmica do piso até 150cm": 0.08
}
impact_piso_sala_quarto = {"Sem piso": -0.12, "Piso laminado": 0.15}
impact_bancadas = {"Louça + pia inox": -0.06, "Granito": 0.14}
impact_itens_esportivos = {"Mini quadra recreativa": 0.05, "Piscina": 0.18}
impact_itens_sociais_ind = {"Espaço pizza": 0.04, "Churrasqueira": 0.09}
impact_facilites = {"Lavanderia": 0.06, "Pet care": 0.03}

# Custos adicionais (R$ por unidade)
custo_parede = {"Apenas cerâmica acima da bancada": 0, "Cerâmica do piso até 150cm": 3_500}
custo_piso_sala_quarto = {"Sem piso": 0, "Piso laminado": 8_000}
custo_bancadas = {"Louça + pia inox": 0, "Granito": 6_500}
custo_itens_esportivos = {"Mini quadra recreativa": 15_000, "Piscina": 50_000}
custo_itens_sociais_ind = {"Espaço pizza": 4_000, "Churrasqueira": 12_000}
custo_facilites = {"Lavanderia": 5_000, "Pet care": 2_500}

# =========================
# AJUSTES POR SEGMENTO (filtros)
# =========================
RENDA_OPCOES = ["4k-5k", "5k-6k", "6k-7k", "7k-8k"]
REGIAO_OPCOES = ["BH e RMBH", "SP e Interior", "RJ", "MG", "ES", "Sul", "NE", "CO/AM"]

mult_renda = {"4k-5k": 0.9, "5k-6k": 1.0, "6k-7k": 1.05, "7k-8k": 1.1}
mult_regiao = {"BH e RMBH": 1.0, "SP e Interior": 1.1, "RJ": 1.05, "MG": 0.98, "ES": 0.97, "Sul": 1.02, "NE": 0.95, "CO/AM": 0.93}

def avg_multiplier(selected, mapping, default=1.0):
    if not selected:
        return default
    return float(np.mean([mapping[s] for s in selected if s in mapping]))

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
# HELPERS PARA SELECTBOX COM PESO
# =========================
def fmt_with_weight(mapping):
    """Retorna uma função format_func para selectbox: 'Nível (+0.12)'."""
    return lambda k: f"{k} ({mapping[k]:+0.2f})"

fmt_parede = fmt_with_weight(impact_parede)
fmt_piso   = fmt_with_weight(impact_piso_sala_quarto)
fmt_banc   = fmt_with_weight(impact_bancadas)
fmt_esp    = fmt_with_weight(impact_itens_esportivos)
fmt_soc    = fmt_with_weight(impact_itens_sociais_ind)
fmt_fac    = fmt_with_weight(impact_facilites)

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
    intent_uplift = adj_score * INTENT_SCALE
    intent_new = np.clip(BASE_INTENT + intent_uplift, 0, 1)
    revenue_add_per_unit = intent_uplift * UNIT_PRICE
    per_unit_net = revenue_add_per_unit - add_cost
    return {
        "Opção": name,
        "SCORE PREFERENCIA": adj_score,
        "Conversão (p.p.)": intent_uplift * 100,
        "Intenção Nova (%)": intent_new * 100,
        "Custo (R$)": add_cost,
        "Receita +/unid (R$)": revenue_add_per_unit,
        "Resultado Líquido +/unid (R$)": per_unit_net
    }

def winner_class(metric_name, a_val, b_val):
    """Retorna a classe CSS ('win'|'lose'|'tie') para A e B, respeitando HIGHER_BETTER."""
    hb = HIGHER_BETTER.get(metric_name, True)
    if abs(a_val - b_val) < 1e-9:
        return "tie", "tie"
    if hb:  # maior é melhor
        return ("win", "lose") if a_val > b_val else ("lose", "win")
    else:   # menor é melhor (apenas custo)
        return ("win", "lose") if a_val < b_val else ("lose", "win")

def badge(label, value, css_class="tie"):
    return f"""
    <div class="metric-box {css_class}">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
    </div>
    """

FMT = {
    "SCORE PREFERENCIA": lambda v: f"{v:.2f}",
    "Conversão (p.p.)":   lambda v: f"{v:.1f}",
    "Intenção Nova (%)":  lambda v: f"{v:.0f}%",
    "Custo (R$)":         lambda v: f"R$ {v:,.0f}",
    "Receita +/unid (R$)":lambda v: f"R$ {v:,.0f}",
    "Resultado Líquido +/unid (R$)": lambda v: f"R$ {v:,.0f}",
}

ROW1 = ["SCORE PREFERENCIA", "Conversão (p.p.)", "Custo (R$)"]
ROW2 = ["Intenção Nova (%)", "Receita +/unid (R$)", "Resultado Líquido +/unid (R$)"]

# =========================
# INPUTS DOS DOIS CARDS
# =========================
st.subheader("1) Duas combinações (A e B)")

colA, colB = st.columns(2)

with colA:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Combinação A")
    c1, c2 = st.columns(2)
    with c1:
        A_parede = st.selectbox("Parede Hidráulica", list(impact_parede.keys()), key="A_parede", format_func=fmt_parede)
        A_piso = st.selectbox("Piso Sala/Quarto", list(impact_piso_sala_quarto.keys()), key="A_piso", format_func=fmt_piso)
        A_banc = st.selectbox("Bancadas", list(impact_bancadas.keys()), key="A_banc", format_func=fmt_banc)
    with c2:
        A_esp = st.selectbox("Itens Esportivos", list(impact_itens_esportivos.keys()), key="A_esportivo", format_func=fmt_esp)
        A_soc = st.selectbox("Itens Sociais Individuais", list(impact_itens_sociais_ind.keys()), key="A_social", format_func=fmt_soc)
        A_fac = st.selectbox("Facilites", list(impact_facilites.keys()), key="A_facil", format_func=fmt_fac)
    st.markdown('</div>', unsafe_allow_html=True)

with colB:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Combinação B")
    c1, c2 = st.columns(2)
    with c1:
        B_parede = st.selectbox("Parede Hidráulica", list(impact_parede.keys()), key="B_parede", format_func=fmt_parede)
        B_piso = st.selectbox("Piso Sala/Quarto", list(impact_piso_sala_quarto.keys()), key="B_piso", format_func=fmt_piso)
        B_banc = st.selectbox("Bancadas", list(impact_bancadas.keys()), key="B_banc", format_func=fmt_banc)
    with c2:
        B_esp = st.selectbox("Itens Esportivos", list(impact_itens_esportivos.keys()), key="B_esportivo", format_func=fmt_esp)
        B_soc = st.selectbox("Itens Sociais Individuais", list(impact_itens_sociais_ind.keys()), key="B_social", format_func=fmt_soc)
        B_fac = st.selectbox("Facilites", list(impact_facilites.keys()), key="B_facil", format_func=fmt_fac)
    st.markdown('</div>', unsafe_allow_html=True)

optA = {"Parede Hidráulica": A_parede, "Piso Sala/Quarto": A_piso, "Bancadas": A_banc,
        "Itens Esportivos": A_esp, "Itens Sociais Individuais": A_soc, "Facilites": A_fac}
optB = {"Parede Hidráulica": B_parede, "Piso Sala/Quarto": B_piso, "Bancadas": B_banc,
        "Itens Esportivos": B_esp, "Itens Sociais Individuais": B_soc, "Facilites": B_fac}

sumA = summarize_option("A", optA, seg_mult)
sumB = summarize_option("B", optB, seg_mult)

# =========================
# HIGHLIGHT DAS MÉTRICAS JÁ NO BLOCO 1
# =========================
colA2, colB2 = st.columns(2)

with colA2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### Métricas — A")

    st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
    for m in ROW1:
        clsA, _ = winner_class(m, sum
