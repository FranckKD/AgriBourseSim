import pandas as pd
import numpy as np
from typing import Dict
from modules.finances.finance_tools import calculer_rendements_dividendes1, calculer_rendements_totaux1
from modules.finances.optimizer import optimiser_portefeuille
from modules.finances.plan_investissement import preparer_flux_capital
from scipy.stats import t

def run_simulation(
    df: pd.DataFrame,
    mode_financement: str,
    params_financement: Dict,
    duree_investissement: int,
    rendement_min_dividendes: float,
    n_simulations: int = 1000,
    aversion_risque: float = 3.0,
    filtrer_stables: bool = True,
    reinvestir_dividendes: bool = True,
    frais_achat: float = 0.012,
    fiscalite_dividendes: float = 0.15,
    taux_sans_risque: float = 0.03,
    min_entreprises: int = 5,
    pond_dividende: float = 0.5,
    mode='hybride'
) -> Dict[str, pd.DataFrame]:

    PROBA_CRISE = 0.05
    FACTEUR_BAISSE_DIV_CRISE = 0.6
    FACTEUR_BAISSE_PV_CRISE = 0.4
    SEUIL_DOWNSIDE = 0.0
    FACTEUR_DOWNSIDE = 0.7
    DEGRES_LIBERTE_T = 5  # pour loi t multivariée

    # Matrice transition Markov 3 états : F, D, C
    regimes = ['favorable', 'defavorable', 'crise']
    trans_mat = {
        'favorable': [0.75, 0.20, 0.05],
        'defavorable': [0.25, 0.55, 0.20],
        'crise': [0.10, 0.20, 0.70],
    }

    resultat = optimiser_portefeuille(
        df=df,
        rendement_dividende_min=rendement_min_dividendes,
        aversion_risque=aversion_risque,
        taux_sans_risque=taux_sans_risque,
        filtrer_stables=filtrer_stables,
        min_entreprises=min_entreprises,
        pond_dividende=pond_dividende,
        mode=mode
    )

    df_portefeuille = resultat['portefeuille']
    titres_optimaux = df_portefeuille['entreprise'].to_list()
    poids_optimaux = df_portefeuille['poids'].values

    rendements_hist = calculer_rendements_totaux1(df)[["Annee"] + titres_optimaux]
    rendements_div = calculer_rendements_dividendes1(df)[["Annee"] + titres_optimaux]

    # Estimation mu/cov par régime sur toute l'historique sans regrouper par régime
    # Ici on suppose qu'on utilise les mêmes mu/cov (par défaut sur toute la période)
    mu = rendements_hist.drop(columns=['Annee']).mean().values
    cov = rendements_hist.drop(columns=['Annee']).cov().values
    mu_div = rendements_div.drop(columns=['Annee']).mean().values

    # Pour différencier les régimes, on peut faire des ajustements manuels
    # Exemple simplifié : 
    mu_fav = mu
    mu_def = mu * 0.8
    mu_cri = mu * 0.5
    cov_fav = cov
    cov_def = cov * 1.5
    cov_cri = cov * 3
    mu_div_fav = mu_div
    mu_div_def = mu_div * 0.7
    mu_div_cri = mu_div * 0.4

    secteurs = df['Secteur'].unique()
    secteur_of = {t: df[df['Nom_Entreprise'] == t]['Secteur'].iloc[0] for t in titres_optimaux}
    titre_idx = {t: i for i, t in enumerate(titres_optimaux)}

    plan_capital = preparer_flux_capital(mode_financement, params_financement, duree_investissement)
    capital_initial = plan_capital["capital_initial"]
    injections = plan_capital["injections_future"]

    np.random.seed(1234)
    simulations_capital = []
    simulations_dividendes = []

    # Initialisation chocs sectoriels persistants
    choc_sectoriel_sim = {s: 0.0 for s in secteurs}

    for _ in range(n_simulations):
        capital = capital_initial
        capital_annuel = []
        dividendes_annuels = []
        regime_actuel = 'favorable'  # init à favorable

        for annee in range(duree_investissement):
            injection = injections.get(annee, 0)
            investissable_net = injection * (1 - frais_achat)
            capital += investissable_net

            # Transition régime Markov
            probs = trans_mat[regime_actuel]
            regime_actuel = np.random.choice(regimes, p=probs)

            # Mise à jour choc sectoriel avec inertie et bruit normal
            for s in secteurs:
                bruit = np.random.normal(0, 0.03)
                choc_sectoriel_sim[s] = 0.7 * choc_sectoriel_sim[s] + bruit
                if regime_actuel == 'crise':
                    choc_sectoriel_sim[s] *= 2

            # Choix des paramètres selon régime
            if regime_actuel == 'favorable':
                mu_rend = mu_fav.copy()
                cov_rend = cov_fav.copy()
                mu_div_rend = mu_div_fav.copy()
            elif regime_actuel == 'defavorable':
                mu_rend = mu_def.copy()
                cov_rend = cov_def.copy()
                mu_div_rend = mu_div_def.copy()
            else:
                mu_rend = mu_cri.copy()
                cov_rend = cov_cri.copy()
                mu_div_rend = mu_div_cri.copy()

            # Ajout chocs sectoriels persistants sur mu_rend
            for titre in titres_optimaux:
                s = secteur_of[titre]
                mu_rend[titre_idx[titre]] += choc_sectoriel_sim[s]

            # Simulation rendements t-multivariés
            try:
                z = t.rvs(df=DEGRES_LIBERTE_T, size=len(titres_optimaux))
                L = np.linalg.cholesky(cov_rend)
                rend_simule = mu_rend + L @ z
            except np.linalg.LinAlgError:
                cov_rend += np.eye(len(titres_optimaux)) * 1e-6
                L = np.linalg.cholesky(cov_rend)
                rend_simule = mu_rend + L @ z

            div_simule = mu_div_rend

            # Baisse en cas de crise
            if regime_actuel == 'crise':
                div_simule *= FACTEUR_BAISSE_DIV_CRISE
                rend_simule *= FACTEUR_BAISSE_PV_CRISE

            rendement_total = np.dot(rend_simule, poids_optimaux)
            rendement_dividende = np.dot(div_simule, poids_optimaux)

            if rendement_total < SEUIL_DOWNSIDE:
                rendement_total *= FACTEUR_DOWNSIDE

            rendement_plus_value = rendement_total - rendement_dividende
            montant_dividendes_bruts = capital * rendement_dividende
            montant_dividendes_nets = montant_dividendes_bruts * (1 - fiscalite_dividendes)

            if reinvestir_dividendes:
                dividendes_annuels.append(montant_dividendes_nets)
                capital *= (1 + rendement_total)
            else:
                capital *= (1 + rendement_plus_value)
                dividendes_annuels.append(montant_dividendes_nets)

            capital_annuel.append(capital)

        simulations_capital.append(capital_annuel)
        simulations_dividendes.append(dividendes_annuels)

    annees_simulees = [rendements_hist['Annee'].max() + i + 1 for i in range(duree_investissement)]
    df_capital = pd.DataFrame(simulations_capital, columns=annees_simulees)
    df_dividendes = pd.DataFrame(simulations_dividendes, columns=annees_simulees)

    resume = {
        "capital_final": np.median(df_capital.iloc[:, -1]),
        "dividendes_cumules_final": np.median(df_dividendes.sum(axis=1)),
        "reinvestissement": reinvestir_dividendes
    }

    return {
        "valeurs_portefeuille": pd.DataFrame([df_capital.median()]),
        "dividendes_cumulees": pd.DataFrame([df_dividendes.median()]),
        "resume": resume,
        "entreprises": df_portefeuille[['entreprise', 'poids']],
    }