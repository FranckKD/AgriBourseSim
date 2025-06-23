# fonctions_utilitaires.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

def allouer_cultures(surface: float, methode: str, cultures: List[str], cultures_db: dict) -> List[Tuple[str, float]]:
    """
    Répartit la surface entre les cultures compatibles avec la méthode (plein_champ ou serre).
    """
    filtres = [c for c in cultures if cultures_db.get(c, {}).get(methode)]
    nb = len(filtres)
    if nb == 0:
        return []
    surface_par_culture = surface / nb
    return [(culture, surface_par_culture) for culture in filtres]

def calculer_mensualite_emprunt(montant: float, taux_annuel: float, duree: int) -> float:
    taux_mensuel = taux_annuel / 12
    n = duree * 12
    return (montant * taux_mensuel) / (1 - (1 + taux_mensuel) ** -n)

def saisonnalite_prix(annee: int, amplitude: float = 0.1, periode: int = 5) -> float:
    phase = (annee % periode) / periode
    facteur = 1 + amplitude * np.sin(2 * np.pi * phase)
    return facteur

def calculer_prix_fluctue(prix: float, sigma: float, risque: Dict, fluctuation_positive: bool = True) -> float:
    if fluctuation_positive:
        base = np.random.normal(prix, prix * sigma)
    else:
        base = np.random.normal(prix, prix * sigma)
        if base > prix:
            base = prix

    if np.random.rand() < risque["proba"]:
        base *= 1 - risque["impact"]

    return max(0, base)

def appliquer_risque_rendement(rendement: float, risque: Dict) -> float:
    if np.random.rand() < risque["proba"]:
        rendement *= 1 - risque["impact"]
    return rendement

def ajuster_rendement_par_meteo(rendement_base: float, pluie: float, temp: float,
                                 sensibilite: float, seuil_pluie_basse: float, seuil_temp_haute: float) -> float:
    facteur = 1.0
    if pluie < seuil_pluie_basse:
        facteur *= (1 - 0.3 * sensibilite)
    if temp > seuil_temp_haute:
        facteur *= (1 - 0.15 * sensibilite)
    return rendement_base * facteur

def appliquer_aléas_climatiques(rendement: float, sensibilite: float,
                                 aleas_climatiques: Dict[str, Dict[str, float]]) -> float:
    facteur = 1.0
    for aléa, params in aleas_climatiques.items():
        if np.random.rand() < params["proba"]:
            impact_effectif = params["impact"] * sensibilite
            facteur *= (1 - impact_effectif)
            if np.random.rand() < 0.1 * sensibilite:
                return 0.0
    return rendement * facteur

def appliquer_impact_climatique(rendement: float, sensibilite: float,
                                 annee_defavorable: bool, impact_climatique_moyen: float) -> float:
    if annee_defavorable:
        perte = sensibilite * impact_climatique_moyen
        rendement *= (1 - perte)
        if np.random.rand() < (sensibilite * 0.5):
            return 0.0
    return rendement

def calculer_impot(benefice_net: float, surface_totale: float,
                   seuil_exoneration_surface: float, taux_imposition: float) -> float:
    if surface_totale >= seuil_exoneration_surface:
        return 0.0
    else:
        return taux_imposition * max(benefice_net, 0)

def calculer_matrices_correlation(meteo_annuelle: pd.DataFrame, prix_annuel: pd.DataFrame,
                                   cultures: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    meteo_climat = pd.DataFrame({culture: meteo_annuelle[f"Pluie_{culture}"] for culture in cultures})
    rendement_climat = meteo_climat.pct_change().dropna()
    prix_cultures = prix_annuel[cultures]
    rendement_prix = prix_cultures.pct_change().dropna()
    matrice_corr_climat = rendement_climat.corr().values
    matrice_corr_prix = rendement_prix.corr().values
    return matrice_corr_climat, matrice_corr_prix

def decouper_cycles_annee(nb_cycles: int, duree_annee: int = 12) -> List[float]:
    if nb_cycles == 0:
        return []
    duree_cycle = duree_annee / nb_cycles
    return [duree_cycle] * nb_cycles
