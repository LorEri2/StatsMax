import pandas as pd
import numpy as np

def charger_donnees(fichiers_csv):
    """
    Charge et combine plusieurs fichiers CSV de football en un seul DataFrame.
    """
    all_dfs = []
    print(f"Chargement de {len(fichiers_csv)} fichiers...")
    
    for f in fichiers_csv:
        try:
            df_temp = pd.read_csv(f, parse_dates=['Date'], dayfirst=True)
            all_dfs.append(df_temp)
        except Exception as e:
            print(f"Avertissement : Impossible de charger le fichier {f}. Erreur : {e}")
            
    if not all_dfs:
        print("Erreur : Aucun fichier n'a pu être chargé.")
        return None
        
    df = pd.concat(all_dfs, ignore_index=True)
    print("Données combinées avec succès.")
    return df

def trouver_plus_longue_serie_moins_0_5_buts(df, nom_equipe):
    """
    Analyse le DataFrame pour trouver la plus longue série de matchs consécutifs
    pour une équipe donnée où le total des buts était inférieur à 0.5 (0 but).
    """
    print(f"\n--- Début de l'analyse pour : {nom_equipe} ---")
    
    colonnes_requises = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
    if not all(col in df.columns for col in colonnes_requises):
        print(f"Erreur : Colonnes manquantes. Assurez-vous d'avoir {colonnes_requises}")
        return

    df_equipe = df[
        (df['HomeTeam'] == nom_equipe) | (df['AwayTeam'] == nom_equipe)
    ].copy()

    if df_equipe.empty:
        print(f"Aucun match trouvé pour l'équipe '{nom_equipe}'.")
        return

    df_equipe = df_equipe.sort_values(by='Date')

    df_equipe['FTHG'] = pd.to_numeric(df_equipe['FTHG'], errors='coerce')
    df_equipe['FTAG'] = pd.to_numeric(df_equipe['FTAG'], errors='coerce')
    
    df_equipe['TotalGoals'] = df_equipe['FTHG'] + df_equipe['FTAG']
    
    # --- LA CONDITION A ÉTÉ MODIFIÉE ICI ---
    # Condition : Vrai si le total de buts est 0
    df_equipe['Under0_5'] = df_equipe['TotalGoals'] < 0.5  # Équivalent à == 0

    # 5. Trouver la plus longue série de "Vrai"
    df_equipe['streak_group'] = (df_equipe['Under0_5'] != df_equipe['Under0_5'].shift()).cumsum()

    # 6. Isoler les séries où la condition est Vraie
    streaks_when_true = df_equipe[df_equipe['Under0_5'] == True]

    if streaks_when_true.empty:
        max_streak = 0
    else:
        streak_lengths = streaks_when_true.groupby('streak_group').size()
        max_streak = streak_lengths.max()

    # 7. Afficher les résultats
    print(f"Nombre total de matchs analysés pour {nom_equipe}: {len(df_equipe)}")
    print(f"Nombre total de matchs avec -0.5 buts (0 but): {len(streaks_when_true)}")
    
    print("\n--- RÉSULTAT ---")
    if max_streak == 0:
        print(f"Aucun match avec 0 but n'a été trouvé pour {nom_equipe}.")
    else:
        print(f"La plus longue série de matchs d'affilée avec -0.5 buts est de : {max_streak}")

# --- POINT D'ENTRÉE DU SCRIPT ---
if __name__ == "__main__":
    fichiers = [
        "PremierLeague2010-2011.csv",
        "PremierLeague2011-2012.csv",
        "PremierLeague2012-2013.csv",
        "PremierLeague2013-2014.csv",
        "PremierLeague2014-2015.csv",
        "PremierLeague2015-2016.csv",
        "PremierLeague2016-2017.csv",
        "PremierLeague2017-2018.csv",
        "PremierLeague2018-2019.csv",
        "PremierLeague2019-2020.csv",
        "PremierLeague2020-2021.csv",
        "PremierLeague2021-2022.csv",
        "PremierLeague2022-2023.csv",
        "PremierLeague2023-2024.csv",
        "PremierLeague2024-2025.csv",
        "PremierLeague2025-2026.csv" 
    ]
    
    equipe_a_analyser = "Bournemouth"
    
    donnees_completes = charger_donnees(fichiers)
    
    if donnees_completes is not None:
        # Appel de la fonction mise à jour
        trouver_plus_longue_serie_moins_0_5_buts(donnees_completes, equipe_a_analyser)