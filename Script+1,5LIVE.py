import pandas as pd
import numpy as np

def charger_tous_les_matchs(fichiers_csv):
    """
    Charge et combine tous les fichiers CSV de l'historique en un seul DataFrame.
    Trie les matchs par date.
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
        
    # Combiner tous les dataframes en un seul
    df = pd.concat(all_dfs, ignore_index=True)
    print("Données combinées avec succès.")
    
    # --- Nettoyage et préparation ---
    colonnes_requises = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
    
    # Supprimer les lignes où les données essentielles sont manquantes
    df = df.dropna(subset=colonnes_requises)
    
    # S'assurer que les dates sont au bon format et trier
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df.sort_values(by='Date')

    # S'assurer que les buts sont numériques
    df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce')
    df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce')
    
    return df

def recuperer_equipes_actuelles(fichier_saison_actuelle):
    """
    Lit le fichier CSV de la saison la plus récente pour obtenir la liste des équipes.
    """
    try:
        df_actuel = pd.read_csv(fichier_saison_actuelle)
        home_teams = df_actuel['HomeTeam'].dropna().unique()
        away_teams = df_actuel['AwayTeam'].dropna().unique()
        equipes_actuelles = sorted(list(set(home_teams) | set(away_teams)))
        print(f"Analyse des {len(equipes_actuelles)} équipes de la saison actuelle.")
        return equipes_actuelles
    except Exception as e:
        print(f"Erreur : Impossible de lire {fichier_saison_actuelle} pour obtenir la liste des équipes. {e}")
        return None

def analyser_series_en_cours(df, equipes):
    """
    Calcule la série en cours pour +1.5 buts pour chaque équipe.
    """
    
    # 1. Calculer la condition pour TOUS les matchs
    df['TotalGoals'] = df['FTHG'] + df['FTAG']
    # Condition : +1.5 buts (2 buts ou plus)
    df['ConditionMet'] = df['TotalGoals'] > 1.5

    resultats = []

    # 2. Boucler sur chaque équipe
    for equipe in equipes:
        # Filtrer tous les matchs de l'équipe, bien triés par date
        df_equipe = df[
            (df['HomeTeam'] == equipe) | (df['AwayTeam'] == equipe)
        ]
        
        serie_en_cours = 0
        
        if not df_equipe.empty:
            # Récupérer la liste des résultats (Vrai/Faux)
            conditions_list = df_equipe['ConditionMet'].tolist()
            
            # 3. Compter "à rebours" depuis le dernier match
            # reversed() parcourt la liste du dernier élément au premier
            for condition_remplie in reversed(conditions_list):
                if condition_remplie:  # C'était Vrai (le match avait +1.5 buts)
                    serie_en_cours += 1
                else:  # C'était Faux (le match avait -1.5 buts)
                    break # La série est rompue, on arrête de compter
        
        resultats.append({
            'Équipe': equipe,
            'Série_en_cours_plus_1_5': serie_en_cours
        })

    # 4. Créer et afficher le rapport
    if resultats:
        df_rapport = pd.DataFrame(resultats)
        # Trier de la plus longue série à la plus courte
        df_rapport = df_rapport.sort_values(by='Série_en_cours_plus_1_5', ascending=False)
        
        print("\n--- Séries en cours : Matchs avec +1.5 Buts (2 ou plus) ---")
        
        # Définir les options d'affichage pour voir toutes les équipes
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', 100) # Ajuster la largeur de l'affichage
        print(df_rapport)
        pd.reset_option('display.max_rows')
        pd.reset_option('display.width')
    else:
        print("Aucun résultat n'a pu être calculé.")

# --- POINT D'ENTRÉE DU SCRIPT ---
if __name__ == "__main__":
    
    # Tous les fichiers d'historique
    fichiers_historique = [
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
    
    # Le fichier le plus récent, utilisé pour savoir quelles équipes analyser
    fichier_actuel = "PremierLeague2025-2026.csv"
    
    # Étape 1 : Charger toutes les données
    donnees_completes = charger_tous_les_matchs(fichiers_historique)
    
    if donnees_completes is not None:
        # Étape 2 : Obtenir la liste des équipes à analyser
        equipes_a_analyser = recuperer_equipes_actuelles(fichier_actuel)
        
        if equipes_a_analyser:
            # Étape 3 : Lancer l'analyse
            analyser_series_en_cours(donnees_completes, equipes_a_analyser)