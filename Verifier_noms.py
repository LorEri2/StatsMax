import pandas as pd

def charger_et_verifier(fichiers_csv):
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
        return

    df = pd.concat(all_dfs, ignore_index=True)
    print("Données combinées avec succès.")

    # Vérifier si les colonnes existent
    if 'HomeTeam' not in df.columns or 'AwayTeam' not in df.columns:
        print("Erreur : Colonnes 'HomeTeam' ou 'AwayTeam' introuvables.")
        return

    # Créer une liste de tous les noms d'équipes
    unique_home_teams = df['HomeTeam'].unique()
    unique_away_teams = df['AwayTeam'].unique()
    
    # Combiner les listes et trier
    all_unique_teams = pd.Series(list(set(unique_home_teams) | set(unique_away_teams))).sort_values()

    print("\n--- LISTE DE TOUS LES NOMS D'ÉQUIPES TROUVÉS ---")
    print(all_unique_teams)
    print("-------------------------------------------------")


# --- POINT D'ENTRÉE DU SCRIPT ---
if __name__ == "__main__":
    fichiers = [
        "PremierLeague2019-2020.csv",
        "PremierLeague2020-2021.csv",
        "PremierLeague2021-2022.csv",
        "PremierLeague2022-2023.csv",
        "PremierLeague2023-2024.csv",
        "PremierLeague2024-2025.csv"
    ]
    
    charger_et_verifier(fichiers)