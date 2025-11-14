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
            df_temp = pd.read_csv(f, parse_dates=['Date'], dayfirst=True)
            all_dfs.append(df_temp)
        except Exception as e:
            print(f"Avertissement : Impossible de charger le fichier {f}. Erreur : {e}")
            
    if not all_dfs:
        print("Erreur : Aucun fichier n'a pu être chargé.")
        return None
        
    df = pd.concat(all_dfs, ignore_index=True)
    print("Données combinées avec succès.")
    
    # --- Préparation des données ---
    # S'assurer que les colonnes de buts finaux existent
    colonnes_requises = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
    df = df.dropna(subset=colonnes_requises) # Supprimer les lignes où elles manquent
    df = df.sort_values(by='Date')
    df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce')
    df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce')
    
    return df

def trouver_record_serie_plus_3_5_buts(df, nom_equipe):
    """
    Analyse le DataFrame pour trouver la plus longue série de matchs consécutifs
    pour une équipe donnée où le total des buts était supérieur à 3.5 (4 ou plus).
    CETTE FONCTION RETOURNE LE RÉSULTAT AU LIEU DE L'AFFICHER.
    """
    
    # 1. Filtrer les matchs de l'équipe
    df_equipe = df[
        (df['HomeTeam'] == nom_equipe) | (df['AwayTeam'] == nom_equipe)
    ].copy()

    if df_equipe.empty:
        return 0 # Retourne 0 si aucune donnée

    # 2. S'assurer du bon ordre chronologique
    df_equipe = df_equipe.sort_values(by='Date')

    # 3. Calculer le total des buts et la condition
    df_equipe['TotalGoals'] = df_equipe['FTHG'] + df_equipe['FTAG']
    df_equipe['Over3_5'] = df_equipe['TotalGoals'] > 3.5 # Équivalent à >= 4

    # 4. Trouver la plus longue série de "Vrai"
    df_equipe['streak_group'] = (df_equipe['Over3_5'] != df_equipe['Over3_5'].shift()).cumsum()
    streaks_when_true = df_equipe[df_equipe['Over3_5'] == True]

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
    
    # Étape 1 : Chargement
    donnees_completes = charger_donnees(fichiers)
    
    if donnees_completes is not None:
        
        # Étape 2 : Obtenir la liste des équipes à analyser
        # On lit le dernier fichier pour savoir quelles équipes sont "actuelles"
        try:
            df_actuel = pd.read_csv("PremierLeague2024-2025.csv")
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
            record_serie = trouver_record_serie_plus_3_5_buts(donnees_completes, equipe)
            
            # Stocker le résultat
            resultats.append({
                'Équipe': equipe,
                'Record_Serie_Plus_3_5_Buts': record_serie
            })

        # Étape 4 : Créer un rapport final, le trier et l'afficher
        df_rapport = pd.DataFrame(resultats)
        df_rapport = df_rapport.sort_values(by='Record_Serie_Plus_3_5_Buts', ascending=False)
        
        print("\n--- RÉSULTAT FINAL : Record historique de séries +3.5 Buts (4 ou plus) ---")
        pd.set_option('display.max_rows', None)
        print(df_rapport)
        pd.reset_option('display.max_rows')