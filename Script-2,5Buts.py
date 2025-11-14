import pandas as pd
import numpy as np
import glob # Pour lire les fichiers dans un dossier
import os   # Pour gérer les noms de fichiers

def sauvegarder_en_html(df_rapport, titre_rapport, nom_fichier):
    """
    Sauvegarde le DataFrame des résultats dans un fichier HTML
    avec une mise en forme CSS.
    """
    try:
        # Convertir le DataFrame pandas en une table HTML
        table_html = df_rapport.to_html(index=False, classes='styled-table', border=0)

        # Style CSS pour un tableau moderne
        html_style = """
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                margin: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
                flex-direction: column;
            }
            h2 {
                color: #333;
            }
            .styled-table {
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 0.9em;
                min-width: 400px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
                width: 60%; /* Ajuster la largeur du tableau */
            }
            .styled-table thead tr {
                background-color: #333333; /* En-tête (sombre pour -2.5) */
                color: #ffffff;
                text-align: left;
            }
            .styled-table th,
            .styled-table td {
                padding: 12px 15px;
                text-align: left;
            }
            .styled-table tbody tr {
                border-bottom: 1px solid #dddddd;
            }
            .styled-table tbody tr:nth-of-type(even) {
                background-color: #f3f3f3; /* Lignes alternées */
            }
            .styled-table tbody tr:last-of-type {
                border-bottom: 2px solid #333333;
            }
        </style>
        """

        # Le contenu HTML complet
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{titre_rapport}</title>
            {html_style}
        </head>
        <body>
            <h2>{titre_rapport}</h2>
            {table_html}
        </body>
        </html>
        """

        # Écrire le contenu dans un fichier
        with open(nom_fichier, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\nSuccès ! Le rapport a été généré ici : {os.path.abspath(nom_fichier)}")

    except Exception as e:
        print(f"\nErreur lors de la génération du fichier HTML : {e}")


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
            print(f"Avertissement : Impossible de charger le fichier {f}. Erreur : {e}")
            
    if not all_dfs:
        print("Erreur : Aucun fichier n'a pu être chargé.")
        return None
        
    df = pd.concat(all_dfs, ignore_index=True)
    print("Données combinées avec succès.")
    
    # Préparation des données FIN DE MATCH
    colonnes_requises = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
    df = df.dropna(subset=colonnes_requises) 
    df = df.sort_values(by='Date')
    df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce')
    df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce')
    
    return df

def trouver_record_serie_moins_2_5_buts(df, nom_equipe):
    """
    Analyse le DataFrame pour trouver la plus longue série de matchs consécutifs
    pour une équipe donnée où le total des buts était inférieur à 2.5 (0, 1 ou 2).
    RETOURNE le résultat (max_streak).
    """
    
    df_equipe = df[
        (df['HomeTeam'] == nom_equipe) | (df['AwayTeam'] == nom_equipe)
    ].copy()

    if df_equipe.empty:
        return 0 

    df_equipe = df_equipe.sort_values(by='Date')
    
    # --- CHANGEMENT DE LOGIQUE ---
    df_equipe['TotalGoals'] = df_equipe['FTHG'] + df_equipe['FTAG']
    # Condition: -2.5 buts (0, 1, ou 2)
    df_equipe['Under2_5'] = df_equipe['TotalGoals'] < 2.5 # Équivalent à <= 2
    
    # Trouver la plus longue série de "Vrai"
    df_equipe['streak_group'] = (df_equipe['Under2_5'] != df_equipe['Under2_5'].shift()).cumsum()
    streaks_when_true = df_equipe[df_equipe['Under2_5'] == True]
    # --- FIN DU CHANGEMENT ---

    if streaks_when_true.empty:
        max_streak = 0
    else:
        streak_lengths = streaks_when_true.groupby('streak_group').size()
        max_streak = streak_lengths.max()

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
        return sorted(list(set(df_complet['HomeTeam'].dropna().unique())))


# --- POINT D'ENTRÉE DU SCRIPT ---
if __name__ == "__main__":
    
    # 1. Définissez le nom de votre dossier ici
    dossier_csv = "CSV_Data" 
    
    # 2. Le script trouve automatiquement tous les CSV
    fichiers_historique = sorted(glob.glob(f"{dossier_csv}/*.csv"))
    
    if not fichiers_historique:
        print(f"Erreur : Aucun fichier .csv n'a été trouvé dans le dossier '{dossier_csv}'")
    else:
        # 3. Il trouve le plus récent tout seul
        fichier_le_plus_recent = fichiers_historique[-1] 
        print(f"Fichier le plus récent détecté : {fichier_le_plus_recent}")
        
        # Étape 1 : Chargement
        donnees_completes = charger_donnees(fichiers_historique)
        
        if donnees_completes is not None:
            
            # Étape 2 : Obtenir la liste des équipes à analyser
            equipes_a_analyser = recuperer_equipes_actuelles(fichier_le_plus_recent, donnees_completes)
            
            # Étape 3 : Boucler, analyser et collecter les résultats
            resultats = []
            
            print("Calcul des records pour chaque équipe... (cela peut prendre un instant)")
            
            for equipe in equipes_a_analyser:
                # --- APPEL DE LA FONCTION MODIFIÉE ---
                record_serie = trouver_record_serie_moins_2_5_buts(donnees_completes, equipe)
                resultats.append({
                    'Équipe': equipe,
                    # --- NOM DE COLONNE MODIFIÉ ---
                    'Record_Serie_Moins_2_5_Buts': record_serie
                })

            # Étape 4 : Créer un rapport final et le trier
            df_rapport = pd.DataFrame(resultats)
            # --- TRI MODIFIÉ ---
            df_rapport = df_rapport.sort_values(by='Record_Serie_Moins_2_5_Buts', ascending=False)
            
            # Étape 5 (Affichage console)
            # --- TITRE MODIFIÉ ---
            print("\n--- RÉSULTAT FINAL : Record historique de séries -2.5 Buts (0-2 buts Fin de Match) ---")
            print(df_rapport)
            
            # --- ÉTAPE 6 (NOUVEAU) : SAUVEGARDE EN HTML ---
            
            # --- TITRE ET NOM DE FICHIER MODIFIÉS ---
            titre_du_rapport = "Record Historique des Séries -2.5 Buts (Premier League)"
            nom_du_fichier_html = "rapport_moins_2_5_buts.html"
            
            # Appel de la nouvelle fonction
            sauvegarder_en_html(df_rapport, titre_du_rapport, nom_du_fichier_html)