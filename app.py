import streamlit as st
from config.settings import APP_NAME, VERSION, APP_LOGO
from pathlib import Path

# 💡 Load custom style
def load_css():
    css_path = Path("assets/style.css")
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 🚀 Page config
st.set_page_config(
    page_title=f"{APP_NAME} | Simulation de rendement de projets",
    page_icon="🌱",
    layout="wide"
)

# 🎨 Load custom CSS
load_css()

# 🧭 Barre de navigation latérale
st.sidebar.image(APP_LOGO, width=120)
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller vers :", ["🏠 Accueil", "📈 Simulation Boursière", "🌾 Simulation Agricole"])


# 📂 Navigation dynamique
if page == "🏠 Accueil":
    import Accueil as accueil
    accueil.run()

elif page == "📈 Simulation Boursière":
    import Simulation_Boursiere as bourse
    bourse.run()

elif page == "🌾 Simulation Agricole":
    import Simulation_Agricole as agricole
    agricole.run()

# 📎 Footer
st.markdown("---")
st.markdown(f"<small>Version {VERSION} • Développé par Franck Emmanuel Djidji Kadjo</small>", unsafe_allow_html=True)
