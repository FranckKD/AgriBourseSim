# simulateur.py
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Tuple
from numpy.random import multivariate_normal

from modules.agriculture.utils import *
from modules.agriculture.finagri import calculer_amortissement_serre
from modules.agriculture.cashflow_cycle import calculer_cashflows_par_cycle

def simuler_projet_agricole(
    surface_totale: float,
    duree_projet: int,
    part_serre: float,
    cultures: List[str],
    cultures_db: Dict,
    seuil_pluie_basse: float,
    seuil_temp_haute: float,
    aleas_climatiques: Dict[str, Dict[str, float]],
    impact_climatique_moyen: float,
    taux_assurance: float,
    taux_imposition: float,
    seuil_exoneration_surface: float,
    taux_charges_sociales: float,
    cout_cmu_par_ouvrier: float,
    nb_ouvriers_par_hectare: float,
    assurance_par_hectare: float,
    surface_serre_unite: float,
    cout_serre_unite: float,
    amortissement_serre_annee: int,
    meteo_annuelle: Optional[pd.DataFrame] = None,
    prix_annuel: Optional[pd.DataFrame] = None,
    mode_financement: str = "autofinancement",
    montant_emprunt: float = 0,
    taux_emprunt: float = 0.02,
    duree_annee: int = 12,
    taux_perte_post_recolte: float = 0.1,
    duree_stockage_mois: int = 1,
    sigma_climat: float = 0.1,
    sigma_prix: float = 0.1
) -> pd.DataFrame:

    surface_serre = surface_totale * part_serre
    surface_plein = surface_totale - surface_serre

    amortissement_annuel_serre = calculer_amortissement_serre(
        surface_serre, surface_serre_unite, cout_serre_unite, amortissement_serre_annee
    ) if surface_serre > 0 else 0.0

    allocation_serre = allouer_cultures(surface_serre, "serre", cultures, cultures_db)
    allocation_plein = allouer_cultures(surface_plein, "plein_champ", cultures, cultures_db)

    mensualite_emprunt = 0
    if mode_financement == "emprunt" and montant_emprunt > 0:
        mensualite_emprunt = calculer_mensualite_emprunt(montant_emprunt, taux_emprunt, duree_projet)

    data = []
    cultures_consideres = [c for c in cultures if cultures_db.get(c, {}).get("plein_champ") or cultures_db.get(c, {}).get("serre")]

    if meteo_annuelle is not None and prix_annuel is not None:
        matrice_corr_climat, matrice_corr_prix = calculer_matrices_correlation(meteo_annuelle, prix_annuel, cultures_consideres)
    else:
        matrice_corr_climat = np.identity(len(cultures_consideres))
        matrice_corr_prix = np.identity(len(cultures_consideres))

    for annee in range(1, duree_projet + 1):
        chocs_climat = multivariate_normal(mean=np.zeros(len(cultures_consideres)),
                                           cov=matrice_corr_climat * sigma_climat ** 2)
        chocs_prix = multivariate_normal(mean=np.zeros(len(cultures_consideres)),
                                         cov=matrice_corr_prix * sigma_prix ** 2)

        annee_defavorable = np.random.rand() < 0.2  # peut être rendu paramétrable aussi si besoin

        pluie, temp = None, None
        if meteo_annuelle is not None and (annee <= len(meteo_annuelle)):
            meteo = meteo_annuelle.iloc[annee - 1]
            pluie = meteo.get("Pluie_annuelle", None)
            temp = meteo.get("Temp_moyenne", None)

        for methode, allocations in [("Serre", allocation_serre), ("Plein champ", allocation_plein)]:
            for culture, surface in allocations:
                params = cultures_db[culture][methode.lower()]
                if params is None:
                    continue

                idx_culture = cultures_consideres.index(culture) if culture in cultures_consideres else None
                chocs_climat_culture = chocs_climat[idx_culture] if idx_culture is not None else 0
                chocs_prix_culture = chocs_prix[idx_culture] if idx_culture is not None else 0

                nb_cycles = params["cycles"]

                flux_cycles = calculer_cashflows_par_cycle(
                    surface=surface,
                    params_culture=params,
                    cycles_par_an=nb_cycles,
                    chocs_climat_cycle=chocs_climat_culture,
                    chocs_prix_cycle=chocs_prix_culture,
                    annee=annee,
                    pluie=pluie,
                    temp=temp,
                    annee_defavorable=annee_defavorable,
                    mensualite_emprunt_mois=mensualite_emprunt,
                    seuil_pluie_basse=seuil_pluie_basse,
                    seuil_temp_haute=seuil_temp_haute,
                    aleas_climatiques=aleas_climatiques,
                    impact_climatique_moyen=impact_climatique_moyen,
                    taux_assurance=taux_assurance,
                    taux_imposition=taux_imposition,
                    seuil_exoneration_surface=seuil_exoneration_surface,
                    taux_charges_sociales=taux_charges_sociales,
                    cout_cmu_par_ouvrier=cout_cmu_par_ouvrier,
                    nb_ouvriers_par_hectare=nb_ouvriers_par_hectare,
                    assurance_par_hectare=assurance_par_hectare,
                    amortissement_annuel_serre=amortissement_annuel_serre if methode.lower() == "serre" else 0.0,
                    stockage_mois=duree_stockage_mois,
                    perte_stock=taux_perte_post_recolte,
                    surface_totale=surface_totale,
                    duree_annee=duree_annee
                )

                for cycle_flux in flux_cycles:
                    data.append({
                        "Année": annee,
                        "Méthode": methode,
                        "Culture": culture,
                        "Surface": round(surface, 2),
                        **cycle_flux
                    })

    return pd.DataFrame(data)

def simuler_projet_agricole_multi(
    n_scenarios: int,
    **kwargs
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scenarios = []
    for i in range(n_scenarios):
        df = simuler_projet_agricole(**kwargs)
        df["Scenario"] = i + 1
        scenarios.append(df)
    df_all = pd.concat(scenarios, ignore_index=True)

    # Calcul des bénéfices nets totaux par scénario
    resume = df_all.groupby("Scenario")["Benefice_net_cycle"].sum().reset_index()
    mediane_val = resume["Benefice_net_cycle"].median()

    # Scénarios min, max, médiane
    idx_min = resume["Benefice_net_cycle"].idxmin()
    idx_max = resume["Benefice_net_cycle"].idxmax()
    idx_med = (resume["Benefice_net_cycle"] - mediane_val).abs().idxmin()

    scenario_min = df_all[df_all["Scenario"] == resume.loc[idx_min, "Scenario"]]
    scenario_max = df_all[df_all["Scenario"] == resume.loc[idx_max, "Scenario"]]
    scenario_med = df_all[df_all["Scenario"] == resume.loc[idx_med, "Scenario"]]

    return df_all, scenario_min, scenario_max, scenario_med