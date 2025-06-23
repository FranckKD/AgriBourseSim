import streamlit as st
import pandas as pd
from modules.finances.simulator_brvm import run_simulation
from modules.finances.optimizer import optimiser_portefeuille
from modules.finances.data_loader import charger_donnees_boursieres
from config.settings import DUREE_INVESTISSEMENT_YEARS
from utils.export_tools import *


if "simulations" not in st.session_state:
    st.session_state["simulations"] = []


@st.cache_data
def get_portefeuille_optimal(
    df,
    rendement_dividende_min,
    aversion_risque,
    taux_sans_risque,
    filtrer_stables,
    min_entreprises,
    pond_dividende,
    mode
):
    return optimiser_portefeuille(
        df=df,
        rendement_dividende_min=rendement_dividende_min,
        aversion_risque=aversion_risque,
        taux_sans_risque=taux_sans_risque,
        filtrer_stables=filtrer_stables,
        min_entreprises=min_entreprises,
        pond_dividende=pond_dividende,
        mode=mode
    )


def run():
    st.title("📈 Simulation Boursière")
    st.markdown("""
        Simulez vos investissements boursiers en définissant vos préférences,
        vos contraintes et vos sources de financement.
    """)

    st.subheader("🎯 Objectifs de l'investisseur")
    duree_investissement = st.number_input(
        "Durée de l'investissement (années)",
        3, 40, DUREE_INVESTISSEMENT_YEARS, step=1
    )
    objectif_rendement_dividende = st.number_input(
        "Rendement minimum annuel des dividendes (%)",
        min_value=0.0, max_value=50.0, value=5.0, step=1.0
    )
    pond_dividende = st.slider(
    label="Pondération des dividendes dans l’objectif",
    min_value=0.0,
    max_value=1.0,
    value=0.5,
    step=0.05,
    help="0 = rendement total uniquement, 1 = rendement dividende uniquement"
    )
    mode = st.radio(
        "Chosissez le mode d'optimisation du portefeuille",
        ["montecarlo", "cvxpy","hybride"]
    )
    aversion_risque = st.slider(
        "Aversion au risque (0 = faible, 10 = élevée)",
        min_value=0.0, max_value=10.0, value=5.0
    )
    taux_sans_risque = st.slider(
        "Taux sans risque (ratio de sharpe=(rendement - taux_sans_risque) / volatilite)",
        min_value=0.00, max_value=1.0, value=0.03, step=0.01
    )
    min_entreprises = st.number_input(
        "Nombre minimum d'actions à inclure",
        min_value=1, max_value=20, value=5
    )
    filtrer_stables = st.checkbox(
        "Ne conserver que les entreprises payant des dividendes stables", value=True
    )
    reinvestir_dividendes = st.checkbox(
        "Réinvestir automatiquement les dividendes perçus", value=True
    )
    frais_achat = st.number_input(
        "Frais d’achat total (%)", min_value=0.0, max_value=5.0, value=1.2
    ) / 100
    fiscalite_dividendes = st.number_input(
        "Fiscalité sur dividendes (%)", min_value=0.0, max_value=50.0, value=15.0
    ) / 100


    st.subheader("💰 Mode de financement")
    mode_financement = st.radio(
        "Choisissez le mode de financement",
        ["Apport mensuel", "Apport unique","Prêt unique", "Prêts multiples"]
    )

    prets = []
    montant_apport_mensuel = 0.0
    montant_apport_unique = 0.0
    duree_prets_total = 0
    params_financement = {}

    if mode_financement == "Apport mensuel":
        montant_apport_mensuel = st.number_input(
            "Montant de l'apport mensuel (FCFA)",
            min_value=0.0, value=100000.0
        )
        params_financement["apport_mensuel"] = montant_apport_mensuel
    
    elif mode_financement == "Apport unique":
        montant_apport_unique = st.number_input(
            "Montant de l'apport unique (FCFA)",
            min_value=0.0, value=1000000.0
        )
        params_financement["apport_unique"] = montant_apport_unique

    elif mode_financement == "Prêt unique":
        montant_pret = st.number_input(
            "Montant du prêt unique (FCFA)",
            min_value=0.0, value=3000000.0
        )
        taux_interet = st.number_input(
            "Taux d'intérêt annuel (%)", min_value=0.0, value=5.0
        )
        duree_pret = st.slider(
            "Durée du prêt (années)", 1, duree_investissement, 5
        )
        if duree_pret > duree_investissement:
            st.warning("La durée du prêt ne peut pas dépasser la durée d'investissement.")
        else:
            prets = {"montant":montant_pret, "taux_annuel":taux_interet, "duree_annees":duree_pret,"annee_debut":0}
        params_financement["prets"] = prets

    else:  # Prêts multiples
        st.markdown("Définissez les différents prêts successifs à inclure.")
        nb_prets = st.number_input("Nombre de prêts", min_value=1, max_value=5, value=2)
        duree_prets_total = 0
        for i in range(nb_prets):
            st.markdown(f"**Prêt {i+1}**")
            annee_debut = st.slider(
                f"Année de début du prêt {i+1}",
                0, duree_investissement - 1, i
            )
            montant = st.number_input(
                f"Montant prêt {i+1} (FCFA)",
                min_value=0.0, value=2000000.0,
                key=f"montant_{i}"
            )
            taux = st.number_input(
                f"Taux intérêt prêt {i+1} (%)",
                min_value=0.0, value=5.0,
                key=f"taux_{i}"
            )
            duree = st.slider(
                f"Durée prêt {i+1} (années)",
                1, duree_investissement - annee_debut, 5,
                key=f"duree_{i}"
            )
            duree_prets_total += duree
            prets.append({"montant":montant, "taux_annuel":taux, "duree_annees":duree,"annee_debut":annee_debut})

        params_financement["prets"] = prets

    if st.button("🚀 Lancer la simulation"):

        #Chargement des données
        df = charger_donnees_boursieres()
        # Validation de base
        if mode_financement == "Apport mensuel" and montant_apport_mensuel == 0:
            st.warning("Veuillez saisir un apport mensuel ou choisir un autre mode de financement.")
            return
        elif mode_financement == "Prêt unique" and not prets:
            st.warning("Veuillez vérifier les paramètres du prêt unique ou choisir un autre mode de financement.")
            return
        elif mode_financement == "Prêts multiples":
            if duree_prets_total > duree_investissement:
                st.warning(f"La somme des durées des prêts ({duree_prets_total} ans) dépasse la durée de l'investissement ({duree_investissement} ans).")
                return
            if not prets:
                st.warning("Veuillez configurer au moins un prêt.")
                return

        st.info("🔍 Optimisation du portefeuille en cours...")
        portefeuille_optimal = get_portefeuille_optimal(
            df=df,
            rendement_dividende_min=objectif_rendement_dividende,
            aversion_risque=aversion_risque,
            taux_sans_risque=taux_sans_risque,
            filtrer_stables=filtrer_stables,
            min_entreprises=min_entreprises,
            pond_dividende=pond_dividende,
            mode=mode
        )

        if len(portefeuille_optimal) == 0:
            st.error("⚠️ Aucun portefeuille ne satisfait le rendement minimum spécifié. Essayez de réduire l'objectif ou vérifiez les données disponibles.")
            return

        st.success("Portefeuille optimal généré ✅")
        st.subheader("📌 Détail du portefeuille optimal")
        st.table(portefeuille_optimal['portefeuille'])

        st.info("📊 Lancement de la simulation ...")
        resultats = run_simulation(
            df=df,
            mode_financement=mode_financement,
            params_financement=params_financement,
            duree_investissement=duree_investissement,
            rendement_min_dividendes=objectif_rendement_dividende,
            n_simulations=1000,
            aversion_risque=aversion_risque,
            filtrer_stables=filtrer_stables,
            reinvestir_dividendes=reinvestir_dividendes,
            frais_achat=frais_achat,
            fiscalite_dividendes=fiscalite_dividendes,
            taux_sans_risque=taux_sans_risque,
            min_entreprises=min_entreprises,
            pond_dividende=pond_dividende,
            mode=mode
        )

        st.success("Simulation terminée ✅")

        df_valeurs = resultats["valeurs_portefeuille"]
        df_dividendes = resultats["dividendes_cumulees"]
        df_resume = resultats["resume"]
        capital_series = df_valeurs.T.squeeze()
        dividende_series = df_dividendes.T.squeeze()

        st.subheader("📈 Évolution du portefeuille")
        st.line_chart(capital_series, use_container_width=True)

        st.subheader("💵 Evolution des dividendes")
        st.bar_chart(dividende_series, use_container_width=True)

        st.subheader("📋 Résumé de la simulation")
        resume_df = pd.DataFrame(resultats["resume"].items(), columns=["Clé", "Valeur"])
        st.table(resume_df)

        
        st.metric("Capital final simulé", f"{resultats['resume']['capital_final']:,.0f} FCFA")

        # Mémorisation des résultats
        st.session_state["resultats_export"] = {
            "Portefeuille Optimal": portefeuille_optimal,
            "Valeurs du Portefeuille": resultats["valeurs_portefeuille"],
            "Revenus de Dividendes": resultats["dividendes_cumulees"],
            "Résumé": resultats["resume"]
        }


        st.markdown("---")
        st.subheader("📤 Exporter les résultats")
        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                label="📥 Exporter en Excel",
                data=export_excel(st.session_state["resultats_export"]),
                file_name="simulation_boursiere.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    run()

