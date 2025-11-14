import pandas as pd
import numpy as np

def charger_donnees(fichiers_csv):
    """
    Charge et combine plusieurs fichiers CSV de football en un seul DataFrame.
    Tente de parser les dates avec le format DD/MM/YYYY.
    """
    all_dfs = []
    print(f"Chargement de {len(fichiers_csv)} fichiers...")
    
    for f in fichiers_csv:
        try:
            # dayfirst=True est important pour les dates au format DD/MM/YYYY
            df_temp = pd.read_csv(f, parse_dates=['Date'], dayfirst=True)
            all_dfs.append(df_temp)
        except Exception as e:
            print(f"Avertissement : Impossible de charger le fichier {f}. Erreur : {e}")
            
    if not all_dfs:
        print("Erreur : Aucun fichier n'a pu être chargé.")
        return None
        
    # Combiner tous les dataframes en un seul
    df = pd.concat(all_dfs, ignore_index=True)
    print("Données combinées avec succès.")
    return df

def trouver_plus_longue_serie_moins_1_5_buts(df, nom_equipe):
    """
    Analyse le DataFrame pour trouver la plus longue série de matchs consécutifs
    pour une équipe donnée où le total des buts était inférieur à 1.5 (0 ou 1).
    """
    print(f"\n--- Début de l'analyse pour : {nom_equipe} ---")
    
    # 1. Vérifier si les colonnes nécessaires existent
    colonnes_requises = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
    if not all(col in df.columns for col in colonnes_requises):
        print(f"Erreur : Colonnes manquantes. Assurez-vous d'avoir {colonnes_requises}")
        return

    # 2. Filtrer les matchs de l'équipe
    # .copy() évite un avertissement SettingWithCopyWarning
    df_equipe = df[
        (df['HomeTeam'] == nom_equipe) | (df['AwayTeam'] == nom_equipe)
    ].copy()

    if df_equipe.empty:
        print(f"Aucun match trouvé pour l'équipe '{nom_equipe}'.")
        return

    # 3. S'assurer du bon ordre chronologique
    df_equipe = df_equipe.sort_values(by='Date')

    # 4. Calculer le total des buts et la condition (-1.5 buts)
    # s'assurer que les buts sont numériques, au cas où
    df_equipe['FTHG'] = pd.to_numeric(df_equipe['FTHG'], errors='coerce')
    df_equipe['FTAG'] = pd.to_numeric(df_equipe['FTAG'], errors='coerce')
    
    # Calculer le total
    df_equipe['TotalGoals'] = df_equipe['FTHG'] + df_equipe['FTAG']
    
    # Créer la condition booléenne : Vrai si 0 ou 1 but, Faux sinon
    df_equipe['Under1_5'] = df_equipe['TotalGoals'] < 1.5

    # 5. Trouver la plus longue série de "Vrai"
    
    # Crée un identifiant unique pour chaque bloc consécutif de Vrai ou Faux
    df_equipe['streak_group'] = (df_equipe['Under1_5'] != df_equipe['Under1_5'].shift()).cumsum()

    # 6. Isoler les séries où la condition est Vraie
    streaks_when_true = df_equipe[df_equipe['Under1_5'] == True]

    if streaks_when_true.empty:
        max_streak = 0
    else:
        # Compter la taille de chaque groupe (série)
        streak_lengths = streaks_when_true.groupby('streak_group').size()
        max_streak = streak_lengths.max()

    # 7. Afficher les résultats
    print(f"Nombre total de matchs analysés pour {nom_equipe}: {len(df_equipe)}")
    print(f"Nombre total de matchs avec -1.5 buts (0 ou 1): {len(streaks_when_true)}")
    
    print("\n--- RÉSULTAT ---")
    if max_streak == 0:
        print(f"Aucune série de matchs avec -1.5 buts n'a été trouvée pour {nom_equipe}.")
    else:
        print(f"La plus longue série de matchs d'affilée avec -1.5 buts est de : {max_streak}")

        # Bonus : Trouver les détails de cette série
        # Récupérer l'ID du groupe de la plus longue série
        longest_streak_group_id = streak_lengths.idxmax()
        
        # Récupérer les matchs de cette série
        longest_streak_df = df_equipe[df_equipe['streak_group'] == longest_streak_group_id]
        
        start_date = longest_streak_df['Date'].min().strftime('%d/%m/%Y')
        end_date = longest_streak_df['Date'].max().strftime('%d/%m/%Y')
        
        print(f"\nCette série de {max_streak} matchs a eu lieu entre le {start_date} et le {end_date}.")
        print("Détails des matchs :")
        print(longest_streak_df[['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'TotalGoals']])

# --- POINT D'ENTRÉE DU SCRIPT ---
if __name__ == "__main__":
    # Liste des fichiers à analyser
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
    
    # Nom de l'équipe à rechercher (doit correspondre exactement au CSV)
    equipe_a_analyser = "Wolves"
    
    # Étape 1 : Chargement
    donnees_completes = charger_donnees(fichiers)
    
    # Étape 2 : Analyse (si le chargement a réussi)
    if donnees_completes is not None:
        trouver_plus_longue_serie_moins_1_5_buts(donnees_completes, equipe_a_analyser)