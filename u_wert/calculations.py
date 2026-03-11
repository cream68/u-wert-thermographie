from handcalcs import handcalc
from handcalcs.global_config import set_option
from pint import UnitRegistry


ureg = UnitRegistry()
Q_ = ureg.Quantity
set_option("preferred_string_formatter", "~L")


def clean_latex_output(latex_code: str) -> str:
    replacements = {
        "degree\\_Celsius": r"^\circ\mathrm{C}",
        "degree_{Celsius}": r"^\circ\mathrm{C}",
        "degreeCelsius": r"^\circ\mathrm{C}",
        "\\mathrm{�C}": r"^\circ\mathrm{C}",
        "�C": r"^\circ\mathrm{C}",
        r"\theta_{i_{norm}}": r"\theta_{i,norm}",
        r"\theta_{e_{norm}}": r"\theta_{e,norm}",
        r"\theta_{io,norm}": r"\theta_{oi,norm}",
        r"\theta_{io_{norm}}": r"\theta_{oi,norm}",
    }
    cleaned = latex_code
    for src, dst in replacements.items():
        cleaned = cleaned.replace(src, dst)
    return cleaned


@handcalc(override="short", precision=3)
def calc_u_i(R_si):
    U_i = 1 / R_si
    return U_i


@handcalc(override="short", precision=3)
def calc_u_e(R_se):
    U_e = 1 / R_se
    return U_e


@handcalc(override="short", precision=3)
def calc_u_innen(theta_i, theta_e, theta_io, U_i):
    U = U_i * (theta_i - theta_io) / (theta_i - theta_e)
    return U


@handcalc(override="short", precision=3)
def calc_u_aussen(theta_i, theta_e, theta_oe, U_e):
    U = U_e * (theta_oe - theta_e) / (theta_i - theta_e)
    return U


@handcalc(override="long", precision=3)
def calc_theta_io_norm_from_u(theta_i_norm, theta_e_norm, U, U_i):
    theta_io_norm = theta_i_norm - (U / U_i) * (theta_i_norm - theta_e_norm)
    return theta_io_norm


@handcalc(override="short", precision=3)
def calc_r_innen(theta_i, theta_e, theta_io, U):
    R_si = (theta_i - theta_io) / (U * (theta_i - theta_e))
    return R_si


@handcalc(override="short", precision=3)
def calc_r_aussen(theta_i, theta_e, theta_oe, U):
    R_se = (theta_oe - theta_e) / (U * (theta_i - theta_e))
    return R_se


def calculate_u(messung: str, theta_i_mess_c: float, theta_e_mess_c: float, theta_surface_mess_c: float, rs_input: float):
    theta_i_mess = Q_(theta_i_mess_c, ureg.degC)
    theta_e_mess = Q_(theta_e_mess_c, ureg.degC)
    theta_surface_mess = Q_(theta_surface_mess_c, ureg.degC)
    R_s = Q_(rs_input, "meter**2 * kelvin / watt")
    U_s = (1 / R_s).to("watt / meter**2 / kelvin")

    dt_mess_total = (theta_i_mess.to("kelvin") - theta_e_mess.to("kelvin")).to("kelvin")
    if abs(dt_mess_total.magnitude) < 1e-12:
        raise ValueError("theta_i,mess und theta_e,mess duerfen nicht gleich sein.")

    if messung == "innen":
        dt_mess_surface = (theta_i_mess.to("kelvin") - theta_surface_mess.to("kelvin")).to("kelvin")
        latex_u_s, U_s_calc = calc_u_i(R_s)
        latex_u, _ = calc_u_innen(theta_i_mess, theta_e_mess, theta_surface_mess, U_s_calc)
    else:
        dt_mess_surface = (theta_surface_mess.to("kelvin") - theta_e_mess.to("kelvin")).to("kelvin")
        latex_u_s, U_s_calc = calc_u_e(R_s)
        latex_u, _ = calc_u_aussen(theta_i_mess, theta_e_mess, theta_surface_mess, U_s_calc)

    U = (U_s * dt_mess_surface / dt_mess_total).to("watt / meter**2 / kelvin")
    return {
        "U": U,
        "latex_u_s": clean_latex_output(latex_u_s),
        "latex_u": clean_latex_output(latex_u),
    }


def calculate_rs_from_u(
    messung: str,
    theta_i_mess_c: float,
    theta_e_mess_c: float,
    theta_surface_mess_c: float,
    u_target_input: float,
):
    theta_i_mess = Q_(theta_i_mess_c, ureg.degC)
    theta_e_mess = Q_(theta_e_mess_c, ureg.degC)
    theta_surface_mess = Q_(theta_surface_mess_c, ureg.degC)
    U_target = Q_(u_target_input, "watt / meter**2 / kelvin")

    if U_target.magnitude <= 0:
        raise ValueError("Der vorgegebene U-Wert muss groesser als 0 sein.")

    dt_mess_total = (theta_i_mess.to("kelvin") - theta_e_mess.to("kelvin")).to("kelvin")
    if abs(dt_mess_total.magnitude) < 1e-12:
        raise ValueError("theta_i,mess und theta_e,mess duerfen nicht gleich sein.")

    if messung == "innen":
        dt_mess_surface = (theta_i_mess.to("kelvin") - theta_surface_mess.to("kelvin")).to("kelvin")
        latex_rs, R_s = calc_r_innen(theta_i_mess, theta_e_mess, theta_surface_mess, U_target)
    else:
        dt_mess_surface = (theta_surface_mess.to("kelvin") - theta_e_mess.to("kelvin")).to("kelvin")
        latex_rs, R_s = calc_r_aussen(theta_i_mess, theta_e_mess, theta_surface_mess, U_target)

    if abs(dt_mess_surface.magnitude) < 1e-12:
        raise ValueError("Die Temperaturdifferenz an der Oberflaeche darf nicht 0 sein.")

    if R_s.magnitude <= 0:
        raise ValueError("Aus den Eingaben ergibt sich ein ungueltiger R_s <= 0.")

    return {
        "R_s": R_s.to("meter**2 * kelvin / watt"),
        "U": U_target,
        "latex_rs": clean_latex_output(latex_rs),
    }


def calculate_norm(theta_i_norm_c: float, theta_e_norm_c: float, r_si_norm: float, U):
    theta_i_norm = Q_(theta_i_norm_c, ureg.degC)
    theta_e_norm = Q_(theta_e_norm_c, ureg.degC)
    R_si_norm = Q_(r_si_norm, "meter**2 * kelvin / watt")
    U_i_norm = (1 / R_si_norm).to("watt / meter**2 / kelvin")
    latex_norm, theta_surface_norm = calc_theta_io_norm_from_u(theta_i_norm, theta_e_norm, U, U_i_norm)
    return clean_latex_output(latex_norm), theta_surface_norm
