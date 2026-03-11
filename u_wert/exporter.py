from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


LATEX_ONLINE_COMPILE_URL = "https://latexonline.cc/compile"


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\\textbackslash{}",
        "&": r"\\&",
        "%": r"\\%",
        "$": r"\\$",
        "#": r"\\#",
        "_": r"\\_",
        "{": r"\\{",
        "}": r"\\}",
        "~": r"\\textasciitilde{}",
        "^": r"\\textasciicircum{}",
    }
    escaped = text
    for src, dst in replacements.items():
        escaped = escaped.replace(src, dst)
    return escaped


def build_latex_report(
    doc_title,
    component_name,
    export_comment,
    messung,
    theta_i_mess_c,
    theta_e_mess_c,
    theta_surface_mess_c,
    rs_input,
    theta_i_norm_c,
    theta_e_norm_c,
    r_si_norm,
    latex_u_s,
    latex_u,
    latex_norm,
    U,
    theta_surface_norm,
):
    surface_label = r"\theta_{io,mess}" if messung == "innen" else r"\theta_{oe,mess}"
    resistance_label = "R_{si}" if messung == "innen" else "R_{se}"
    norm_surface_label = r"\theta_{oi,norm}"
    escaped_title = latex_escape(doc_title)
    escaped_component = latex_escape(component_name)
    escaped_comment = latex_escape(export_comment.strip())
    comment_block = ""
    if escaped_comment:
        comment_block = escaped_comment + "\n\n"

    return f"""\\documentclass[a4paper,11pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[ngerman]{{babel}}
\\usepackage{{amsmath}}
\\usepackage{{geometry}}
\\geometry{{margin=2.2cm}}

\\title{{{escaped_title}}}
\\author{{Bauteil: {escaped_component}}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle

{comment_block}

\\section*{{Eingaben}}
Messart: {messung},
$\\theta_{{i,mess}}={theta_i_mess_c:.1f}\\,^\\circ\\mathrm{{C}}$,
$\\theta_{{e,mess}}={theta_e_mess_c:.1f}\\,^\\circ\\mathrm{{C}}$,
${surface_label}={theta_surface_mess_c:.1f}\\,^\\circ\\mathrm{{C}}$,
${resistance_label}={rs_input:.2f}\\,\\mathrm{{m^2K/W}}$\\newline
$\\theta_{{i,norm}}={theta_i_norm_c:.1f}\\,^\\circ\\mathrm{{C}}$,
$\\theta_{{e,norm}}={theta_e_norm_c:.1f}\\,^\\circ\\mathrm{{C}}$,
$R_{{si,norm}}={r_si_norm:.2f}\\,\\mathrm{{m^2K/W}}$.

\\section*{{Berechnung}}
{latex_u_s}

{latex_u}

{latex_norm}

\\section*{{Ausgabe}}
\\[
\\boxed{{
\\begin{{aligned}}
U &= {U.magnitude:.3f}\\,\\frac{{\\mathrm{{W}}}}{{\\mathrm{{m^2K}}}} \\\\
{norm_surface_label} &= {theta_surface_norm.magnitude:.3f}\\,^\\circ\\mathrm{{C}}
\\end{{aligned}}
}}
\\]

\\end{{document}}
"""


def compile_latex_to_pdf_bytes(latex_source: str):
    try:
        query = urlencode(
            {
                "text": latex_source,
                "command": "pdflatex",
                "download": "report.pdf",
                "force": "true",
            }
        )
        url = f"{LATEX_ONLINE_COMPILE_URL}?{query}"

        with urlopen(url, timeout=45) as response:
            pdf_bytes = response.read()
            content_type = (response.headers.get("Content-Type") or "").lower()

        if "application/pdf" not in content_type and not pdf_bytes.startswith(b"%PDF"):
            details = pdf_bytes.decode("utf-8", errors="replace").strip()
            if len(details) > 1200:
                details = details[:1200] + " ..."
            return None, f"LaTeX-Online lieferte keine PDF: {details}"

        return pdf_bytes, ""
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace").strip()
        if len(details) > 1200:
            details = details[:1200] + " ..."
        return None, f"LaTeX-Online Fehler ({exc.code}): {details}"
    except URLError as exc:
        return None, f"LaTeX-Online nicht erreichbar: {exc.reason}"
