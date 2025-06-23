import streamlit as st
from config.settings import APP_NAME

def run():
    st.title(f"Bienvenue sur {APP_NAME} 🌿📊")
    st.markdown(
        """
        <div class='intro'>
            <h3>Une solution tout-en-un pour planifier vos investissements.</h3>
            <p>
                AgriBourseSim vous permet de <strong>simuler et optimiser</strong> vos investissements en bourse 
                ainsi que d’évaluer la <strong>rentabilité de projets agricoles</strong> sur le long terme.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Présentation des deux modules
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Simulation Boursière")
        st.markdown(
            """
            - Définissez vos préférences de rendement minimum (dividendes).
            - Choisissez votre mode de financement : **apport mensuel** ou **prêt unique/multiple**.
            - Générez un portefeuille optimal.
            - Simulez vos gains annuels avec la méthode **Monte Carlo**.
            """
        )

    with col2:
        st.subheader("🌾 Simulation Agricole")
        st.markdown(
            """
            - Comparez deux méthodes : **culture sous serre** vs **culture sans serre**.
            - Estimez les coûts, rendements, marges nettes et ROI sur 10 ans.
            - Intégrez les effets de l’inflation, de l’endettement et de la saisonnalité.
            """
        )

    # Appel à l'action
    st.markdown("---")
    st.success("🚀 Commencez dès maintenant en sélectionnant une section dans le menu à gauche.")

if __name__ == "__main__":
    run()