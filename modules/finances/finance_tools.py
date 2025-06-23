import pandas as pd
import numpy as np

def verifier_colonnes(df: pd.DataFrame, colonnes_attendues: set):
    """
    Vérifie que le DataFrame contient toutes les colonnes attendues.
    """
    manquantes = colonnes_attendues - set(df.columns)
    if manquantes:
        raise ValueError(f"Colonnes manquantes : {manquantes}")

def calculer_rendements_totaux(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les rendements totaux annuels = (cours actuel - cours précédent + dividende) / cours précédent.

    Returns:
        pd.DataFrame: Rendements totaux annuels avec Année en index et Nom_Entreprise en colonnes.
    """
    
    df = df.copy()
    df['Annee'] = df['Annee'].astype(int)
    df.sort_values(['Nom_Entreprise', 'Annee'], inplace=True)
    df['Cours_Precedent'] = df.groupby('Nom_Entreprise')['Prix_Cloture_Annuel'].shift(1)
    df = df[df['Cours_Precedent'].notna() & (df['Cours_Precedent'] != 0)]
    df['Rendement_Total'] = (df['Prix_Cloture_Annuel'] - df['Cours_Precedent'] + df['Dividende_Verse']) / df['Cours_Precedent']
    
    return df.pivot(index='Annee', columns='Nom_Entreprise', values='Rendement_Total')

def calculer_rendements_totaux1(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les rendements totaux annuels = (cours actuel - cours précédent + dividende) / cours précédent.

    Returns:
        pd.DataFrame: Rendements totaux annuels avec Année en index et Nom_Entreprise en colonnes.
    """
    
    df = df.copy()
    df['Annee'] = df['Annee'].astype(int)
    df['Rendement_Dividende'] = df['Rendement_Dividende']/100
    df.sort_values(['Nom_Entreprise', 'Annee'], inplace=True)
    df['Cours_Precedent'] = df.groupby('Nom_Entreprise')['Prix_Cloture_Annuel'].shift(1)
    df = df[df['Cours_Precedent'].notna() & (df['Cours_Precedent'] != 0)]
    df['Rendement_Total'] = (df['Prix_Cloture_Annuel'] - df['Cours_Precedent'] + df['Dividende_Verse']) / df['Cours_Precedent']
    
    return df.pivot(index='Annee', columns='Nom_Entreprise', values='Rendement_Total').reset_index()

def calculer_rendements_dividendes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les rendements dividendes annuels.

    Returns:
        pd.DataFrame: Rendements dividendes annuels avec Année en index et Nom_Entreprise en colonnes.
    """
    
    df = df.copy()
    if 'Annee' not in df.columns:
        raise ValueError("Colonnes du DataFrame dans calculer_rendements_dividendes:", df.columns.tolist())

    df['Annee'] = df['Annee'].astype(int)
    
    return df.pivot(index='Annee', columns='Nom_Entreprise', values='Rendement_Dividende')

def calculer_rendements_dividendes1(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les rendements dividendes annuels.

    Returns:
        pd.DataFrame: Rendements dividendes annuels avec Année en index et Nom_Entreprise en colonnes.
    """
    
    df = df.copy()
    if 'Annee' not in df.columns:
        raise ValueError("Colonnes du DataFrame dans calculer_rendements_dividendes:", df.columns.tolist())

    df['Annee'] = df['Annee'].astype(int)
    df['Rendement_Dividende'] = df['Rendement_Dividende']/100
    
    return df.pivot(index='Annee', columns='Nom_Entreprise', values='Rendement_Dividende').reset_index()

def extraire_moyenne_dividendes(df: pd.DataFrame) -> pd.Series:
    """
    Calcule le rendement moyen en dividendes par actif.

    Returns:
        pd.Series: Moyenne du rendement dividende par Ticker.
    """
    rendements_div = calculer_rendements_dividendes(df)
    return rendements_div.mean()

def extraire_moyenne_rendements(df: pd.DataFrame) -> pd.Series:
    """
    Calcule le rendement moyen en dividendes par actif.

    Returns:
        pd.Series: Moyenne du rendement dividende par Ticker.
    """
    rendements_tot = calculer_rendements_totaux(df)
    return rendements_tot.mean()

def matrice_covariance_dividendes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Matrice de covariance des dividendes.

    Returns:
        pd.DataFrame: Matrice de covariance (Nom_Entreprise x Nom_Entreprise).
    """
    rendements_div = calculer_rendements_dividendes(df)
    return rendements_div.cov()

def matrice_covariance_rendements(df: pd.DataFrame) -> pd.DataFrame:
    """
    Matrice de covariance des rendements totaux.

    Returns:
        pd.DataFrame: Matrice de covariance (Nom_Entreprise x Nom_Entreprise).
    """
    rendements_tot = calculer_rendements_totaux(df)
    return rendements_tot.cov()

def filtrer_payeurs_stables(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtre les tickers avec 'Payeur_Stable' == 'true' ou 'oui'.

    Returns:
        pd.DataFrame: Sous-ensemble du DataFrame avec uniquement les payeurs stables.
    """
    verifier_colonnes(df, {'Payeur_Stable'})
    
    df = df.copy()
    df['Payeur_Stable'] = df['Payeur_Stable'].astype(str).str.lower()
    return df[df['Payeur_Stable'].isin(['true', 'oui'])]

def filtrer_entreprises_valides(df):
    """
    Retourne les entreprises ayant des données complètes pour toutes les années disponibles.

    Paramètres :
    - df : DataFrame contenant les colonnes 'Nom_Entreprise' et 'Annee'

    Retourne :
    - liste d'entreprises valides
    """
    df = df.copy()
    entreprises_all = df['Nom_Entreprise'].unique()
    annees = df['Annee'].unique()
    entreprises_valides = [
        e for e in entreprises_all
        if df[df['Nom_Entreprise'] == e].shape[0] == len(annees)
    ]
    return entreprises_valides

