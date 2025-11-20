import pandas as pd
import glob
import os

# --- 1. CONFIGURATION ---
DOSSIER_CSV = "CSV_Data/data2025" 
FICHIER_SORTIE = "rapport_sans_nul.html"

LIGUES_CIBLES = {
    'F1': '🇫🇷 Ligue 1', 'F2': '🇫🇷 Ligue 2',
    'D1': '🇩🇪 Bundesliga', 'D2': '🇩🇪 Bundesliga 2',
    'SP1': '🇪🇸 La Liga', 'SP2': '🇪🇸 La Liga 2',
    'I1': '🇮🇹 Serie A',
    'E0': '🇬🇧 Premier League', 'E1': '🇬🇧 Championship'
}

def standardiser_colonnes(df):
    mapping = {
        'Home': 'HomeTeam', 'Home Team': 'HomeTeam',
        'Away': 'AwayTeam', 'Away Team': 'AwayTeam',
        'Res': 'FTR', 'Result': 'FTR', 'FTR': 'FTR',
        'Date': 'Date', 'Match Date': 'Date'
    }
    return df.rename(columns=mapping)

def calculer_serie_sans_nul(df_equipe):
    df_equipe = df_equipe.sort_values(by='Date', ascending=False)
    serie = 0
    for resultat in df_equipe['FTR']:
        if resultat != 'D': serie += 1
        else: break
    return serie

def formater_details_html(details_str):
    """Transforme 'V, D, V' en petites pastilles colorées"""
    html = ""
    for res in details_str.split(', '):
        color = "#28a745" if res == 'H' or res == 'A' or res == 'V' else "#dc3545" # Vert pour Victoire (simplifié), Rouge pour Défaite
        # Note: Dans le fichier CSV, 'H'/'A' sont les vainqueurs. 
        # Pour simplifier l'affichage visuel ici sans re-calculer qui a gagné exactement:
        # On va garder le texte brut mais le mettre dans une pastille grise si on est pas sûr, 
        # ou on laisse le texte simple.
        # Mieux : on garde le texte brut.
        pass
    return details_str

def generer_html(df_resultats):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Séries Sans Match Nul</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f6f9; padding: 20px; color: #333; }}
            .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h1 {{ text-align: center; color: #2c3e50; margin-bottom: 10px; }}
            .subtitle {{ text-align: center; color: #7f8c8d; margin-bottom: 30px; }}
            
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background-color: #34495e; color: white; padding: 12px 15px; text-align: left; font-weight: 600; }}
            td {{ padding: 12px 15px; border-bottom: 1px solid #eee; }}
            tr:hover {{ background-color: #f8f9fa; }}
            
            .serie-val {{ font-weight: bold; font-size: 1.1em; color: #e67e22; }}
            .ligue-badge {{ font-size: 0.85em; color: #7f8c8d; }}
            .team-name {{ font-weight: 600; color: #2c3e50; }}
            
            /* Highlight pour les très grosses séries */
            .fire {{ color: #c0392b; font-weight: bold; }}
            tr.top-serie td {{ background-color: #fff8e1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚫 Séries "Sans Match Nul"</h1>
            <p class="subtitle">Équipes n'ayant pas fait de match nul depuis au moins <strong>3 matchs</strong>.</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Ligue</th>
                        <th>Équipe</th>
                        <th style="text-align:center">Série en cours</th>
                        <th>Derniers Résultats</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for _, row in df_resultats.iterrows():
        ligue = row['Ligue']
        equipe = row['Équipe']
        serie = row['Série Sans Nul']
        details = row['Détails']
        
        row_class = "top-serie" if serie >= 8 else ""
        fire_icon = "🔥 " if serie >= 8 else ""
        
        html_content += f"""
        <tr class="{row_class}">
            <td class="ligue-badge">{ligue}</td>
            <td class="team-name">{equipe}</td>
            <td style="text-align:center"><span class="serie-val">{fire_icon}{serie}</span></td>
            <td style="color:#666; font-size:0.9em;">{details}</td>
        </tr>
        """
        
    html_content += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ Rapport généré : {os.path.abspath(FICHIER_SORTIE)}")

def main():
    print(f"🔍 Analyse des séries...")
    resultats_globaux = []

    for code_ligue, nom_ligue in LIGUES_CIBLES.items():
        fichier = os.path.join(DOSSIER_CSV, f"{code_ligue}.csv")
        if not os.path.exists(fichier): continue

        try:
            try: df = pd.read_csv(fichier, on_bad_lines='skip')
            except: df = pd.read_csv(fichier, on_bad_lines='skip', encoding='latin1')
            
            df = standardiser_colonnes(df)
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            if df['Date'].isna().mean() > 0.8:
                 df['Date'] = pd.to_datetime(df['Date'], dayfirst=False, errors='coerce')
            df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam', 'FTR'])

            equipes = sorted(list(set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())))
            
            for equipe in equipes:
                df_eq = df[(df['HomeTeam'] == equipe) | (df['AwayTeam'] == equipe)]
                serie = calculer_serie_sans_nul(df_eq)
                
                if serie >= 3:
                    # Récupérer les résultats pour l'affichage
                    # Note: FTR = H (Home Win), A (Away Win), D (Draw)
                    # Pour simplifier l'affichage, on montre juste le FTR brut
                    derniers_res = df_eq.sort_values('Date', ascending=False)['FTR'].head(serie).tolist()
                    str_res = ", ".join(derniers_res[:5])
                    if len(derniers_res) > 5: str_res += "..."
                    
                    resultats_globaux.append({
                        'Ligue': nom_ligue,
                        'Équipe': equipe,
                        'Série Sans Nul': serie,
                        'Détails': str_res
                    })

        except Exception as e:
            print(f"Erreur {nom_ligue}: {e}")

    if resultats_globaux:
        df_final = pd.DataFrame(resultats_globaux)
        df_final = df_final.sort_values(by=['Série Sans Nul', 'Ligue'], ascending=[False, True])
        generer_html(df_final)
    else:
        print("Aucune série trouvée.")

if __name__ == "__main__":
    main()