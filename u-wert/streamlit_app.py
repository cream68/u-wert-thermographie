import streamlit as st
from datetime import date
import re

from calculations import calculate_norm, calculate_rs_from_u, calculate_u
from exporter import build_latex_report, compile_latex_to_pdf_bytes


def init_state() -> None:
    defaults = {
        "doc_title": "U-Wert Nachweis",
        "component_name": "Außenwand Nord",
        "export_comment": "",
        "theta_i_mess_c": 20.0,
        "theta_e_mess_c": -5.0,
        "theta_surface_mess_c": 16.0,
        "r_si_value": 0.13,
        "r_se_value": 0.04,
        "r_si_norm_value": 0.13,
        "reverse_rs_mode": False,
        "u_target_value": 0.35,
        "theta_i_norm_c": 20.0,
        "theta_e_norm_c": -5.0,
    }
    if "theta_e_mess_c" not in st.session_state and "theta_a_mess_c" in st.session_state:
        st.session_state.theta_e_mess_c = st.session_state.theta_a_mess_c
    if "theta_e_norm_c" not in st.session_state and "theta_a_norm_c" in st.session_state:
        st.session_state.theta_e_norm_c = st.session_state.theta_a_norm_c
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def safe_filename_part(text: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", text).strip()
    return cleaned or "Bauteil"


st.set_page_config(page_title="U-Wert Rechner", layout="centered")
st.title("U-Wert aus Thermografie")
st.caption("Rueckrechnung aus Innen- oder Aussenmessung")
init_state()

messung = st.radio("Messung", ["innen", "außen"], horizontal=True)

with st.sidebar:
    doc_title = st.text_input("Überschrift für Export", key="doc_title")
    component_name = st.text_input("Bauteilbezeichnung", key="component_name")
    export_comment = st.text_area("Kommentar für Export", key="export_comment")
    st.divider()

    with st.popover("Info: Rsi/Rse"):
        st.image("Rsi_Rse.png", caption="Rsi/Rse (Oberflaechenwiderstaende)")

    with st.popover("Info: Herleitung U"):
        if messung == "innen":
            st.latex(r"q = U\,(\theta_i-\theta_e) = U_i\,(\theta_i-\theta_{io})")
            st.latex(r"\Rightarrow U = U_i\,\frac{\theta_i-\theta_{io}}{\theta_i-\theta_e}")
        else:
            st.latex(r"q = U\,(\theta_i-\theta_e) = U_e\,(\theta_{oe}-\theta_e)")
            st.latex(r"\Rightarrow U = U_e\,\frac{\theta_{oe}-\theta_e}{\theta_i-\theta_e}")

    with st.popover("Info: Herleitung theta_oi,norm"):
        st.latex(r"U_{i}\,(\theta_{o}-\theta_{i,norm}) = U\,(\theta_{i,norm}-\theta_{e,norm})")
        st.latex(r"\theta_{o} = \theta_{i,norm} - \frac{U}{U_i}\,(\theta_{i,norm}-\theta_{e,norm})")

theta_i_mess_c = st.number_input("gemessene Innentemperatur °C", step=0.5, key="theta_i_mess_c")
theta_e_mess_c = st.number_input("gemessene Außentemperatur °C", step=0.5, key="theta_e_mess_c")
theta_surface_mess_c = st.number_input("gemessene Bauteiltemperatur °C", step=0.5, key="theta_surface_mess_c")

reverse_rs_mode = st.toggle(
    "R_si/R_se rueckrechnen (U-Wert vorgeben)",
    value=bool(st.session_state.reverse_rs_mode),
    key="reverse_rs_mode",
)

calc_error = None
calc_result = None
u_target_value = None
rs_input = float(st.session_state.r_si_value if messung == "innen" else st.session_state.r_se_value)

if reverse_rs_mode:
    u_target_value = st.number_input(
        "vorgegebener U-Wert W/(m²K)",
        min_value=0.0001,
        step=0.01,
        format="%.3f",
        value=float(st.session_state.u_target_value),
        key="u_target_input",
    )
    st.session_state.u_target_value = float(u_target_value)

    try:
        rs_result = calculate_rs_from_u(
            messung,
            theta_i_mess_c,
            theta_e_mess_c,
            theta_surface_mess_c,
            u_target_value,
        )
        rs_input = float(rs_result["R_s"].magnitude)
        if messung == "innen":
            st.session_state.r_si_value = rs_input
            st.caption(f"Erforderlich: R_si = {rs_input:.4f} m²K/W")
        else:
            st.session_state.r_se_value = rs_input
            st.caption(f"Erforderlich: R_se = {rs_input:.4f} m²K/W")

        calc_result = {
            "U": rs_result["U"],
            "latex_u_s": rs_result["latex_rs"],
            "latex_u": "",
        }
    except ValueError as exc:
        calc_error = str(exc)
else:
    if messung == "innen":
        rs_input = st.number_input(
            "Wärmeübergangswiderstand R_si",
            min_value=0.0001,
            step=0.0001,
            format="%.4f",
            value=float(st.session_state.r_si_value),
            key="r_si_input",
        )
        st.session_state.r_si_value = float(rs_input)
    else:
        rs_input = st.number_input(
            "Wärmeübergangswiderstand R_se",
            min_value=0.01,
            step=0.01,
            format="%.2f",
            value=float(st.session_state.r_se_value),
            key="r_se_input",
        )
        st.session_state.r_se_value = float(rs_input)

if not reverse_rs_mode:
    try:
        calc_result = calculate_u(messung, theta_i_mess_c, theta_e_mess_c, theta_surface_mess_c, rs_input)
    except ValueError as exc:
        calc_error = str(exc)

if calc_error or calc_result is None:
    st.error(calc_error or "Berechnung konnte nicht durchgefuehrt werden.")
else:
    U = calc_result["U"]
    latex_u_s = calc_result["latex_u_s"]
    latex_u = calc_result["latex_u"]

    st.markdown(latex_u_s)
    st.markdown(latex_u)

    with st.expander("Normbedingungen nach DIN 4108-2", expanded=False):
        theta_i_norm_c = st.number_input("Norminnentemperatur °C", step=0.5, key="theta_i_norm_c")
        theta_e_norm_c = st.number_input("Normaußentemperatur °C", step=0.5, key="theta_e_norm_c")

        if messung == "innen":
            r_si_norm = float(st.session_state.r_si_value)
            st.caption(f"Verwendet R_si aus oben: {r_si_norm:.2f} m²K/W")
        else:
            r_si_norm = st.number_input(
                "Innenwiderstand R_si fuer Normbedingung",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                value=float(st.session_state.r_si_norm_value),
                key="r_si_norm_input",
            )
            st.session_state.r_si_norm_value = float(r_si_norm)

        latex_norm, theta_surface_norm = calculate_norm(theta_i_norm_c, theta_e_norm_c, r_si_norm, U)
        st.markdown(latex_norm)

    latex_report = build_latex_report(
        doc_title=doc_title,
        component_name=component_name,
        export_comment=export_comment,
        messung=messung,
        theta_i_mess_c=theta_i_mess_c,
        theta_e_mess_c=theta_e_mess_c,
        theta_surface_mess_c=theta_surface_mess_c,
        rs_input=rs_input,
        theta_i_norm_c=theta_i_norm_c,
        theta_e_norm_c=theta_e_norm_c,
        r_si_norm=r_si_norm,
        latex_u_s=latex_u_s,
        latex_u=latex_u,
        latex_norm=latex_norm,
        U=U,
        theta_surface_norm=theta_surface_norm,
    )

    pdf_bytes, pdf_error = compile_latex_to_pdf_bytes(latex_report)
    if pdf_bytes is not None:
        export_name = f"{date.today().isoformat()} U-Wert {safe_filename_part(component_name)}.pdf"
        st.download_button(
            "PDF Export (.pdf)",
            data=pdf_bytes,
            file_name=export_name,
            mime="application/pdf",
        )
    else:
        st.warning(pdf_error)
