# interface_streamlit.py
import streamlit as st
import pandas as pd
from modules.agriculture.simulator_agri import simuler_projet_agricole_multi
from config import cultures_db
from utils.export_tools import export_excel


def run():
    st.set_page_config(page_title="Simulateur Agricole", layout="wide")
    st.title("🌾 Simulation Monte Carlo Agricole")

    st.markdown("""
    Cette page vous permet de simuler la rentabilité d’un projet agricole en analysant plusieurs scénarios aléatoires.
    Le simulateur applique une logique Monte Carlo pour estimer la distribution des résultats.
    """)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        duree = st.slider("Durée du projet (en années)", min_value=1, value=5)
        surface_ha = st.number_input("Surface totale (en hectares)", min_value=0.1, value=1.0, step=0.1)
        part_serre = st.slider("Part de la surface en serre (%)", 0, 100, 0)
        cultures = st.multiselect("Cultures sélectionnées", list(cultures_db.keys()))

    with col2:
        n_scenarios = st.slider("Nombre de scénarios Monte Carlo", 10, 500, 100, step=10)
        taux_emprunt = st.number_input("Taux d'emprunt (%)", value=2.0) / 100
        montant_emprunt = st.number_input("Montant emprunté (FCFA)", value=0.0)
        mode_financement = "emprunt" if montant_emprunt > 0 else "autofinancement"

    st.divider()

    if st.button("Lancer la simulation"):

        resultats, scen_min, scen_max, scen_med = simuler_projet_agricole_multi(
            n_scenarios=n_scenarios,
            surface_totale=surface_ha,
            duree_projet=duree,
            part_serre=part_serre / 100,
            cultures=cultures,
            cultures_db=cultures_db,
            seuil_pluie_basse=1000,
            seuil_temp_haute=30.0,
            aleas_climatiques={
                "sécheresse": {"proba": 0.15, "impact": 0.4},
                "inondation": {"proba": 0.10, "impact": 0.5},
                "tempête": {"proba": 0.05, "impact": 0.3},
            },
            impact_climatique_moyen=0.3,
            taux_assurance=0.02,
            taux_imposition=0.15,
            seuil_exoneration_surface=5.0,
            taux_charges_sociales=0.20,
            cout_cmu_par_ouvrier=12000,
            nb_ouvriers_par_hectare=0.5,
            assurance_par_hectare=5000,
            surface_serre_unite=0.05,
            cout_serre_unite=1200000,
            amortissement_serre_annee=10,
            mode_financement=mode_financement,
            montant_emprunt=montant_emprunt,
            taux_emprunt=taux_emprunt
        )

        st.success("Simulation terminée ✅")

        st.subheader("📊 Résumé des scénarios clés")

        col1, col2, col3 = st.columns(3)

        col1.metric("Scénario Minimum", f"{scen_min['Benefice_net_cycle'].sum():,.0f} FCFA")
        col2.metric("Scénario Médian", f"{scen_med['Benefice_net_cycle'].sum():,.0f} FCFA")
        col3.metric("Scénario Maximum", f"{scen_max['Benefice_net_cycle'].sum():,.0f} FCFA")

        st.divider()
        st.subheader("📈 Distribution des bénéfices nets")

        chart_data = resultats.groupby("Scenario")["Benefice_net_cycle"].sum().reset_index()
        st.bar_chart(chart_data.set_index("Scenario"))

        st.divider()
        st.subheader("📤 Exporter les résultats")

        export_data = {
            "Tous les scénarios": resultats,
            "Scénario Minimum": scen_min,
            "Scénario Maximum": scen_max,
            "Scénario Médian": scen_med,
        }

        st.download_button(
            label="📥 Exporter en Excel",
            data=export_excel(export_data),
            file_name="simulation_agricole_montecarlo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    run()
