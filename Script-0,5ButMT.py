import pandas as pd
import numpy as np

def charger_donnees(fichiers_csv):
    """
    Charge et combine plusieurs fichiers CSV de football en un seul DataFrame.
    Prépare les données pour l'analyse de la MI-TEMPS.
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
    
    # --- Préparation des données MI-TEMPS ---
    # !!! CHANGEMENT : On vérifie HTHG et HTAG (mi-temps) !!!
    colonnes_requises = ['Date', 'HomeTeam', 'AwayTeam', 'HTHG', 'HTAG']
    df = df.dropna(subset=colonnes_requises) # Supprimer les lignes où elles manquent
    df = df.sort_values(by='Date')
    df['HTHG'] = pd.to_numeric(df['HTHG'], errors='coerce')
    df['HTAG'] = pd.to_numeric(df['HTAG'], errors='coerce')
    
    return df

def trouver_record_serie_moins_0_5_buts_MT(df, nom_equipe):
    """
    Analyse le DataFrame pour trouver la plus longue série de matchs consécutifs
    pour une équipe donnée où le total des buts à la MI-TEMPS était inférieur à 0.5 (0 but).
    RETOURNE le résultat (max_streak).
    """
    
    # 1. Filtrer les matchs de l'équipe
    df_equipe = df[
        (df['HomeTeam'] == nom_equipe) | (df['AwayTeam'] == nom_equipe)
    ].copy()

    if df_equipe.empty:
        return 0 # Retourne 0 si aucune donnée

    # 2. S'assurer du bon ordre chronologique
    df_equipe = df_equipe.sort_values(by='Date')

    # 3. Calculer le total des buts MI-TEMPS et la condition
    df_equipe['TotalHTGoals'] = df_equipe['HTHG'] + df_equipe['HTAG']
    
    # --- LA CONDITION A ÉTÉ MODIFIÉE ICI ---
    # Créer la condition booléenne : Vrai si 0 but en MT
    df_equipe['Under0_5_HT'] = df_equipe['TotalHTGoals'] < 0.5 # Équivalent à == 0

    # 4. Trouver la plus longue série de "Vrai"
    df_equipe['streak_group'] = (df_equipe['Under0_5_HT'] != df_equipe['Under0_5_HT'].shift()).cumsum()
    streaks_when_true = df_equipe[df_equipe['Under0_5_HT'] == True]

    if streaks_when_true.empty:
        max_streak = 0
    else:
        streak_lengths = streaks_when_true.groupby('streak_group').size()
        max_streak = streak_lengths.max()

    # 5. Retourner le résultat
    return max_streak

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
        "PremierLeague2024-2025.csv" 
    ]
    
    # Étape 1 : Chargement (les données MT sont préparées ici)
    donnees_completes = charger_donnees(fichiers)
    
    if donnees_completes is not None:
        
        # Étape 2 : Obtenir la liste des équipes à analyser
        # On lit le dernier fichier pour savoir quelles équipes sont "actuelles"
        try:
            df_actuel = pd.read_csv("PremierLeague2025-2026.csv")
            equipes_domicile = df_actuel['HomeTeam'].dropna().unique()
            equipes_exterieur = df_actuel['AwayTeam'].dropna().unique()
            equipes_actuelles = sorted(list(set(equipes_domicile) | set(equipes_exterieur)))
            print(f"Analyse des {len(equipes_actuelles)} équipes de la saison 2024-2025.")
        except Exception as e:
            print(f"Erreur lecture dernier fichier, on prend toutes les équipes de l'historique: {e}")
            equipes_actuelles = sorted(list(set(donnees_completes['HomeTeam'])))

        
        # Étape 3 : Boucler, analyser et collecter les résultats
        resultats = []
        
        print("Calcul des records pour chaque équipe... (cela peut prendre un instant)")
        
        for equipe in equipes_actuelles:
            # Appel de la fonction d'analyse (qui retourne maintenant un nombre)
            record_serie = trouver_record_serie_moins_0_5_buts_MT(donnees_completes, equipe)
            
            # Stocker le résultat
            resultats.append({
                'Équipe': equipe,
                'Record_Serie_Moins_0_5_MT': record_serie
            })

        # Étape 4 : Créer un rapport final, le trier et l'afficher
        df_rapport = pd.DataFrame(resultats)
        df_rapport = df_rapport.sort_values(by='Record_Serie_Moins_0_5_MT', ascending=False)
        
        print("\n--- RÉSULTAT FINAL : Record historique de séries -0.5 Buts MT (0-0 à la MT) ---")
        pd.set_option('display.max_rows', None)
        print(df_rapport)
        pd.reset_option('display.max_rows')