# cashflow_cycle.py
from typing import Dict, List, Optional
import numpy as np
from modules.agriculture.finagri import calculer_couts_cycle
from modules.agriculture.utils import (
    ajuster_rendement_par_meteo,
    appliquer_risque_rendement,
    appliquer_aléas_climatiques,
    appliquer_impact_climatique,
    calculer_impot,
    calculer_prix_fluctue,
    saisonnalite_prix
)

def calculer_cashflows_par_cycle(
    surface: float,
    params_culture: dict,
    cycles_par_an: int,
    chocs_climat_cycle: float,
    chocs_prix_cycle: float,
    annee: int,
    pluie: Optional[float],
    temp: Optional[float],
    annee_defavorable: bool,
    mensualite_emprunt_mois: float,
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
    amortissement_annuel_serre: float = 0.0,
    stockage_mois: int = 1,
    perte_stock: float = 0.1,
    surface_totale: float = 0,
    duree_annee: int = 12
) -> List[Dict]:

    duree_cycle_mois = duree_annee / cycles_par_an
    flux_cycles = []
    stock_en_cours = 0.0

    for cycle_index in range(cycles_par_an):
        rendement = params_culture["rendement"]
        prix = params_culture["prix"]
        sigma = params_culture["sigma"]
        risque_rendement = params_culture["risque_rendement"]
        risque_prix = params_culture["risque_prix"]
        sensibilite = params_culture["sensibilite_climat"]

        rendement = ajuster_rendement_par_meteo(rendement, pluie, temp, sensibilite, seuil_pluie_basse, seuil_temp_haute) if pluie and temp else rendement
        rendement *= (1 + chocs_climat_cycle)
        rendement = appliquer_risque_rendement(rendement, risque_rendement)
        rendement = appliquer_aléas_climatiques(rendement, sensibilite, aleas_climatiques)
        rendement = appliquer_impact_climatique(rendement, sensibilite, annee_defavorable, impact_climatique_moyen)

        prix_base = prix * (1 + chocs_prix_cycle)
        facteur_saison = saisonnalite_prix(annee)
        prix_reel = calculer_prix_fluctue(prix_base * facteur_saison, sigma, risque_prix, fluctuation_positive=True)

        production_cycle = rendement * surface * 1000
        couts_fixes, cout_assurance_ha = calculer_couts_cycle(
            params_culture, surface, duree_cycle_mois,
            taux_charges_sociales, cout_cmu_par_ouvrier,
            nb_ouvriers_par_hectare, assurance_par_hectare,
            amortissement_annuel_serre, duree_annee
        )

        ca_cycle = production_cycle * prix_reel
        cout_assurance = max(taux_assurance * ca_cycle, cout_assurance_ha)
        couts = couts_fixes + cout_assurance

        remboursement_cycle = mensualite_emprunt_mois * duree_cycle_mois

        vente_stock = stock_en_cours * (1 - perte_stock)
        stock_en_cours = production_cycle

        benefice_brut_cycle = vente_stock * prix_reel + ca_cycle - couts - remboursement_cycle
        impot_cycle = calculer_impot(benefice_brut_cycle, surface_totale, seuil_exoneration_surface, taux_imposition)
        benefice_net_cycle = benefice_brut_cycle - impot_cycle

        flux_cycles.append({
            "Cycle": cycle_index + 1,
            "Production_cycle_kg": production_cycle,
            "Stock_entrant_kg": stock_en_cours,
            "Vente_stock_kg": vente_stock,
            "Prix_reel": prix_reel,
            "CA_cycle": round(ca_cycle + vente_stock * prix_reel, 0),
            "Couts": round(couts, 0),
            "Remboursement_cycle": round(remboursement_cycle, 0),
            "Impots": round(impot_cycle, 0),
            "Benefice_net_cycle": round(benefice_net_cycle, 0),
        })

    return flux_cycles
