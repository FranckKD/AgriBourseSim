import pandas as pd
from typing import List, Dict

class Pret:
    def __init__(self, montant: float, taux_annuel: float, duree_annees: int, annee_debut: int):
        self.montant = montant
        self.taux_annuel = taux_annuel
        self.duree_annees = duree_annees
        self.annee_debut = annee_debut

    def plan_remboursement(self) -> pd.DataFrame:
        n_annees = self.duree_annees
        annuite = self.montant * (self.taux_annuel) / (1 - (1 + self.taux_annuel) ** -n_annees)

        remboursements = []
        montant_restant = self.montant
        for annee in range(n_annees):
            interet = montant_restant * self.taux_annuel
            principal = annuite - interet
            montant_restant -= principal
            remboursements.append({
                'Annee': self.annee_debut + annee,
                'Annuite': annuite,
                'Principal': principal,
                'Interet': interet
            })
        return pd.DataFrame(remboursements)

def extraire_flux_capital(prets: List[Pret], duree_totale_annees: int) -> Dict:
    capital_initial = sum([p.montant for p in prets if p.annee_debut == 0])
    injections = {}
    for pret in prets:
        if pret.annee_debut > 0:
            injections[pret.annee_debut] = injections.get(pret.annee_debut, 0) + pret.montant
    return {
        'capital_initial': capital_initial,
        'injections_future': injections
    }

def preparer_flux_capital(mode_financement: str, params: Dict, duree: int) -> Dict:
    if mode_financement == "Apport unique":
        return {
            "capital_initial": params.get("apport_unique", 0.0),
            "injections_future": {}
        }

    elif mode_financement == "Prêt unique":
        pret = Pret(**params["prets"])
        return extraire_flux_capital([pret], duree)


    elif mode_financement == "Prêts multiples":
        prets = [Pret(**d) for d in params["prets"]]
        return extraire_flux_capital(prets, duree)

    elif mode_financement == "Apport mensuel":
        montant_annuel = params["apport_mensuel"] * 12
        injections = {annee: montant_annuel for annee in range(duree)}
        return {
            "capital_initial": 0.0,
            "injections_future": injections
        }

    else:
        raise ValueError(f"Mode de financement inconnu : {mode_financement}")