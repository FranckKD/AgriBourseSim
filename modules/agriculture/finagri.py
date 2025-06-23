# finances.py
from typing import Dict, Tuple

def calculer_amortissement_serre(surface_serre: float,
                                  surface_serre_unite: float,
                                  cout_serre_unite: float,
                                  amortissement_serre_annee: int) -> float:
    nb_unites = surface_serre / surface_serre_unite
    cout_total = nb_unites * cout_serre_unite
    amortissement_annuel = cout_total / amortissement_serre_annee
    return amortissement_annuel

def calculer_couts_cycle(
    params_culture: dict,
    surface: float,
    duree_cycle_mois: float,
    taux_charges_sociales: float,
    cout_cmu_par_ouvrier: float,
    nb_ouvriers_par_hectare: float,
    assurance_par_hectare: float,
    amortissement_annuel_serre: float = 0.0,
    duree_annee: int = 12
) -> Tuple[float, float]:

    cout_intrants = params_culture["cout_intrants"]
    cout_main_oeuvre = params_culture["cout_main_oeuvre"]
    cout_charges_sociales = taux_charges_sociales * cout_main_oeuvre
    cout_cmu = cout_cmu_par_ouvrier * nb_ouvriers_par_hectare * surface * (duree_cycle_mois / duree_annee)
    cout_assurance_ha = assurance_par_hectare * surface * (duree_cycle_mois / duree_annee)

    amortissement_cycle = amortissement_annuel_serre * (duree_cycle_mois / duree_annee)

    total_couts = (
        cout_intrants + cout_main_oeuvre + cout_charges_sociales + cout_cmu + amortissement_cycle
    )
    return total_couts, cout_assurance_ha
