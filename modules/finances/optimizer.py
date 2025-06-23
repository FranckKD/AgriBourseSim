import numpy as np
import pandas as pd
import cvxpy as cp
from modules.finances.finance_tools import *

def optimiser_portefeuille(
    df,
    rendement_dividende_min=0.02,
    aversion_risque=0.0,
    taux_sans_risque=0.03,
    filtrer_stables=True,
    min_entreprises=5,
    pond_dividende=0.5,
    mode="hybride",
    n_simulations=5000,
    poids_max=0.25,
    poids_min=0.05,
    random_state=42,
    afficher_logs=False
):
    """
    Optimisation d'un portefeuille BRVM avec pondération dividende vs rendement total.

    Paramètres :
    - pond_dividende = 1 : priorité au rendement dividende
    - pond_dividende = 0 : priorité au rendement total
    """
    # Vérification colonnes nécessaires
    required_cols = [
        'Nom_Entreprise', 'Prix_Cloture_Annuel', 'Dividende_Verse',
        'Variation(annee_precedente)', 'Annee'
    ]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Colonne manquante : {col}")

    df = df.copy()
    df.dropna(subset=['Prix_Cloture_Annuel', 'Dividende_Verse'], inplace=True)

    if filtrer_stables:
        df = filtrer_payeurs_stables(df)

    # Calcul du rendement dividende moyen
    rendements_div = extraire_moyenne_dividendes(df)
    
    # Filtrage en amont selon rendement_dividende_min
    entreprises_valides = rendements_div[rendements_div >= rendement_dividende_min].index.tolist()
    df = df[df['Nom_Entreprise'].isin(entreprises_valides)]

    entreprises = df['Nom_Entreprise'].unique()
    if len(entreprises) < min_entreprises:
        raise ValueError("Nombre d'entreprises valides insuffisant après filtrage.")

    # Recalcul après filtrage
    
    rendements_cours = df.groupby('Nom_Entreprise')['Variation(annee_precedente)'].mean()
    rendements_totaux = rendements_div + rendements_cours
    cov_matrix = df.pivot(index='Annee', columns='Nom_Entreprise', values='Variation(annee_precedente)').cov().fillna(0).values

    def monte_carlo():
        np.random.seed(random_state)
        best_score = -np.inf
        best_w = None
        n = len(entreprises)

        for _ in range(n_simulations):
            w = np.random.rand(n)
            w /= w.sum()
            if np.any(w > poids_max):
                continue

            rend_div = np.dot(w, rendements_div.loc[entreprises])
            if rend_div < rendement_dividende_min:
                continue

            rend_tot = np.dot(w, rendements_totaux.loc[entreprises])
            vol = np.sqrt(w.T @ cov_matrix @ w)
            score = pond_dividende * rend_div + (1 - pond_dividende) * rend_tot - aversion_risque * vol

            if score > best_score:
                best_score = score
                best_w = w

        if best_w is None:
            raise ValueError("Aucune solution valide trouvée par Monte Carlo.")

        poids = best_w
        entreprises_sel = [entreprises[i] for i in range(n) if poids[i] > 1e-4]
        poids_sel = [poids[i] for i in range(n) if poids[i] > 1e-4]

        portf_df = pd.DataFrame({
            'entreprise': entreprises_sel,
            'poids': poids_sel,
            'rendement_dividende': rendements_div.loc[entreprises_sel].values,
            'rendement_total': rendements_totaux.loc[entreprises_sel].values
        })

        stats = {
            'rendement_espere': float(np.dot(poids, rendements_totaux.loc[entreprises])),
            'rendement_dividende': float(np.dot(poids, rendements_div.loc[entreprises])),
            'volatilite': float(np.sqrt(poids.T @ cov_matrix @ poids)),
            'sharpe_ratio': float((np.dot(poids, rendements_totaux.loc[entreprises]) - taux_sans_risque) /
                                  np.sqrt(poids.T @ cov_matrix @ poids))
        }
        return portf_df, stats

    def cvxpy_optim(df_sub):
        entreprises_sub = df_sub['Nom_Entreprise'].unique()
        n_sub = len(entreprises_sub)

        rend_div_sub = extraire_moyenne_dividendes(df_sub)
        rend_cours_sub = df_sub.groupby('Nom_Entreprise')['Variation(annee_precedente)'].mean()
        rend_tot_sub = rend_div_sub + rend_cours_sub

        cov_sub = df_sub.pivot(index='Annee', columns='Nom_Entreprise', values='Variation(annee_precedente)').cov().fillna(0).values

        w = cp.Variable(n_sub)
        z = cp.Variable(n_sub, boolean=True)

        Sigma_sqrt = np.linalg.cholesky(cov_sub + 1e-6 * np.eye(n_sub))
        volatilite = cp.norm(Sigma_sqrt @ w, 2)

        objectif = cp.Maximize(
            pond_dividende * rend_div_sub.values @ w +
            (1 - pond_dividende) * rend_tot_sub.values @ w -
            aversion_risque * volatilite
        )

        contraintes = [
            cp.sum(w) == 1,
            w >= 0,
            w <= poids_max * z,
            w >= poids_min * z,
            rend_div_sub.values @ w >= rendement_dividende_min,
            cp.sum(z) >= min_entreprises
        ]

        probleme = cp.Problem(objectif, contraintes)
        try:
            probleme.solve(solver=cp.ECOS_BB)
        except Exception as e:
            raise ValueError(f"Erreur d'optimisation CVXPY : {e}")

        if probleme.status not in ["optimal", "optimal_inaccurate"]:
            raise ValueError("Optimisation CVXPY échouée.")

        poids_opt = w.value
        entreprises_sel = [entreprises_sub[i] for i in range(n_sub) if poids_opt[i] > 1e-4]
        poids_sel = [poids_opt[i] for i in range(n_sub) if poids_opt[i] > 1e-4]

        portf_df = pd.DataFrame({
            'entreprise': entreprises_sel,
            'poids': poids_sel,
            'rendement_dividende': rend_div_sub.loc[entreprises_sel].values,
            'rendement_total': rend_tot_sub.loc[entreprises_sel].values
        })

        stats = {
            'rendement_espere': float(np.dot(poids_opt, rend_tot_sub.values)),
            'rendement_dividende': float(np.dot(poids_opt, rend_div_sub.values)),
            'volatilite': float(np.sqrt(poids_opt.T @ cov_sub @ poids_opt)),
            'sharpe_ratio': float((np.dot(poids_opt, rend_tot_sub.values) - taux_sans_risque) /
                                  np.sqrt(poids_opt.T @ cov_sub @ poids_opt))
        }

        return portf_df, stats

    # Mode d'optimisation
    if mode == "montecarlo":
        portefeuille, stats = monte_carlo()
    elif mode == "cvxpy":
        try:
            portefeuille, stats = cvxpy_optim(df)
        except ValueError:
            if afficher_logs:
                print("⚠️ CVXPY échoué, repli sur Monte Carlo.")
            portefeuille, stats = monte_carlo()
    elif mode == "hybride":
        port_mc, stat_mc = monte_carlo()
        entreprises_filtrees = port_mc['entreprise'].tolist()
        df_sub = df[df['Nom_Entreprise'].isin(entreprises_filtrees)]
        try:
            portefeuille, stats = cvxpy_optim(df_sub)
        except ValueError:
            if afficher_logs:
                print("⚠️ Hybride : CVXPY échoué, retour Monte Carlo.")
            portefeuille, stats = port_mc, stat_mc
    else:
        raise ValueError("Mode inconnu : utiliser 'montecarlo', 'cvxpy' ou 'hybride'.")

    if afficher_logs:
        print("📊 Portefeuille optimisé :", portefeuille)
        print("📈 Statistiques :", stats)

    return {
        'portefeuille': portefeuille,
        'stats': stats
    }