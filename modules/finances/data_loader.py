import pandas as pd
import os

def charger_donnees_boursieres(fichier="data/donnees_brvm.xlsx") -> pd.DataFrame:
    if not os.path.exists(fichier):
        raise FileNotFoundError(f"Fichier non trouvé : {fichier}")
    
    df = pd.read_excel(fichier)

    # Nettoyage éventuel
    df.columns = [col.strip() for col in df.columns]
    df['Nom_Entreprise'] = df['Nom_Entreprise'].str.upper()

    # Vérification des colonnes obligatoires
    colonnes_attendues = {"Nom_Entreprise","Secteur","Annee","Prix_Cloture_Annuel","Variation(annee_precedente)","Dividende_Verse","Nombre_Actions_restant",
                          	"Capital_restant","Rendement_Dividende","Payeur_Stable"}
    if not colonnes_attendues.issubset(df.columns):
        raise ValueError(f"Colonnes manquantes dans le fichier Excel : {colonnes_attendues - set(df.columns)}")

    return df