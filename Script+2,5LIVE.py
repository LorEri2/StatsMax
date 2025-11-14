import pandas as pd
import numpy as np

def charger_donnees(fichiers_csv):
    """
    Charge et combine plusieurs fichiers CSV de football en un seul DataFrame.
    Prépare les données pour l'analyse de FIN DE MATCH.
    """
    all_dfs = []
    print(f"Chargement de {len(fichiers_csv)} fichiers...")
    
    for f in fichiers_csv:
        try:
            df_temp = pd.read_csv(f, parse_dates=['Date'], dayfirst=True)
            all_dfs.append(df_temp)
        except Exception as e:
            # Gérer le cas où le fichier 2019-2020 a un nom différent
            if "PremierLeague2019-2020csv.csv" in f:
                try:
                    df_temp_alt = pd.read_csv("PremierLeague2019-2020.csv", parse_dates=['Date'], dayfirst=True)
                    all_dfs.append(df_temp_alt)
                    print("Info : 'PremierLeague2019-2020csv.csv' non trouvé, 'PremierLeague2019-2020.csv' chargé.")
                except Exception as e_alt:
                    print(f"Avertissement : Impossible de charger {f} ou sa variante. Erreur : {e_alt}")
            else:
                print(f"Avertissement : Impossible de charger le fichier {f}. Erreur : {e}")
            
    if not all_dfs:
        print("Erreur : Aucun fichier n'a pu être chargé.")
        return None
        
    df = pd.concat(all_dfs, ignore_index=True)
    print("Données combinées avec succès.")
    
    # --- Préparation des données FIN DE MATCH ---
    # !!! CHANGEMENT : On vérifie FTHG et FTAG (Fin de Match) !!!
    colonnes_requises = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
    df = df.dropna(subset=colonnes_requises) # Supprimer les lignes où elles manquent
    df = df.sort_values(by='Date')
    df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce')
    df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce')
    
    return df

def trouver_record_serie_plus_2_5_buts(df, nom_equipe):
    """
    Analyse le DataFrame pour trouver la plus longue série de matchs consécutifs
    pour une équipe donnée où le total des buts était supérieur à 2.5 (3 ou plus).
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

    # 3. Calculer le total des buts Fin de Match et la condition
    df_equipe['TotalGoals'] = df_equipe['FTHG'] + df_equipe['FTAG']
    
    # --- LA CONDITION A ÉTÉ MODIFIÉE ICI ---
    # Créer la condition booléenne : Vrai si 3 buts ou plus (Fin de Match)
    df_equipe['Over2_5'] = df_equipe['TotalGoals'] > 2.5 # Équivalent à >= 3

    # 4. Trouver la plus longue série de "Vrai"
    df_equipe['streak_group'] = (df_equipe['Over2_5'] != df_equipe['Over2_5'].shift()).cumsum()
    streaks_when_true = df_equipe[df_equipe['Over2_5'] == True]

    if streaks_when_true.empty:
        max_streak = 0
    else:
        streak_lengths = streaks_when_true.groupby('streak_group').size()
        max_streak = streak_lengths.max()

    # 5. Retourner le résultat
    return max_streak

def recuperer_equipes_actuelles(fichier_saison_actuelle, df_complet):
    """
    Lit le fichier CSV de la saison la plus récente pour obtenir la liste des équipes.
    """
    try:
        df_actuel = pd.read_csv(fichier_saison_actuelle)
        equipes_domicile = df_actuel['HomeTeam'].dropna().unique()
        equipes_exterieur = df_actuel['AwayTeam'].dropna().unique()
        equipes_actuelles = sorted(list(set(equipes_domicile) | set(equipes_exterieur)))
        print(f"Analyse des {len(equipes_actuelles)} équipes de la saison {fichier_saison_actuelle}.")
        return equipes_actuelles
    except Exception as e:
        print(f"Erreur lecture dernier fichier '{fichier_saison_actuelle}', on prend toutes les équipes de l'historique: {e}")
        # Fallback : prendre toutes les équipes de l'historique complet
        return sorted(list(set(df_complet['HomeTeam'].dropna().unique())))


# --- POINT D'ENTRÉE DU SCRIPT ---
if __name__ == "__main__":
    
    # La liste de fichiers complète basée sur vos ajouts
    fichiers = [
        "PremierLeague2010-2011.csv",
        "PremierLeague2011-2012.csv",
        "PremierLeague2012-2013.csv",
        "PremierLeague2013-2014.csv",
        "PremierLeague2014-2015.csv",
        "PremierLeague2015-2016.csv", # Corrigé
        "PremierLeague2016-2017.csv",
        "PremierLeague2017-2018.csv",
        "PremierLeague2018-2019.csv",
        "PremierLeague2019-2020csv.csv", # Fichier que vous avez uploadé
        "PremierLeague2020-2021.csv",
        "PremierLeague2021-2022.csv",
        "PremierLeague2022-2023.csv",
        "PremierLeague2023-2024.csv",
        "PremierLeague2024-2025.csv",
        "PremierLeague2025-2026.csv"  # Le dernier fichier
    ]
    
    # Le fichier le plus récent pour la liste des équipes
    fichier_le_plus_recent = "PremierLeague2025-2026.csv"
    
    # Étape 1 : Chargement
    donnees_completes = charger_donnees(fichiers)
    
    if donnees_completes is not None:
        
        # Étape 2 : Obtenir la liste des équipes à analyser
        equipes_a_analyser = recuperer_equipes_actuelles(fichier_le_plus_recent, donnees_completes)
        
        # Étape 3 : Boucler, analyser et collecter les résultats
        resultats = []
        
        print("Calcul des records pour chaque équipe... (cela peut prendre un instant)")
        
        for equipe in equipes_a_analyser:
            # Appel de la fonction d'analyse
            record_serie = trouver_record_serie_plus_2_5_buts(donnees_completes, equipe)
            
            # Stocker le résultat
            resultats.append({
                'Équipe': equipe,
                'Record_Serie_Plus_2_5_Buts': record_serie
            })

        # Étape 4 : Créer un rapport final, le trier et l'afficher
        df_rapport = pd.DataFrame(resultats)
        df_rapport = df_rapport.sort_values(by='Record_Serie_Plus_2_5_Buts', ascending=False)
        
        print("\n--- RÉSULTAT FINAL : Record historique de séries +2.5 Buts (3+ buts Fin de Match) ---")
        pd.set_option('display.max_rows', None)
        print(df_rapport)
        pd.reset_option('display.max_rows')