import pandas as pd
import glob
import os

# --- CONFIGURATION DES LIGUES ---
# Codes CSV et Noms d'affichage
LIGUES_A_ANALYSER = {
    'F1': 'Ligue 1',
    'F2': 'Ligue 2',
    'D1': 'Bundesliga',
    'D2': 'Bundesliga 2',
    'SP1': 'La Liga',
    'SP2': 'La Liga 2',
    'I1': 'Serie A',
    'E0': 'Premier League',
    'E1': 'Championship'

}

DOSSIER_PRINCIPAL = "CSV_Data"
FICHIER_SORTIE = "rapport_over15_multi.html"
SAISON_ACTUELLE_DOSSIER = "data2025" 

def standardiser_colonnes(df):
    """Assure que les colonnes ont les bons noms."""
    mapping = {
        'Home': 'HomeTeam', 'Home Team': 'HomeTeam',
        'Away': 'AwayTeam', 'Away Team': 'AwayTeam',
        'HG': 'FTHG', 'FTHG': 'FTHG',
        'AG': 'FTAG', 'FTAG': 'FTAG',
        'Date': 'Date'
    }
    return df.rename(columns=mapping)

def get_current_teams(dossier_base, ligue_code):
    """Récupère la liste des équipes de la saison actuelle pour filtrer."""
    # On cherche le fichier .csv (ex: F1.csv) dans le dossier 2025
    chemin_actuel = os.path.join(dossier_base, SAISON_ACTUELLE_DOSSIER, f"{ligue_code}.csv")
    
    if not os.path.exists(chemin_actuel):
        return None # Fichier pas trouvé, on ne filtre pas (ou on skip)
    
    try:
        try: df = pd.read_csv(chemin_actuel, on_bad_lines='skip')
        except: df = pd.read_csv(chemin_actuel, on_bad_lines='skip', encoding='latin1')
        
        df = standardiser_colonnes(df)
        equipes = set(df['HomeTeam'].dropna().unique()) | set(df['AwayTeam'].dropna().unique())
        return list(equipes)
    except:
        return None

def analyser_ligue(code_ligue, nom_ligue):
    """Analyse l'historique complet pour UNE ligue."""
    print(f"Traitement de {nom_ligue} ({code_ligue})...")
    
    # 1. Équipes actuelles
    equipes_actuelles = get_current_teams(DOSSIER_PRINCIPAL, code_ligue)
    if not equipes_actuelles:
        print(f"   ⚠️ Pas de données 2025 trouvées pour {code_ligue}. Sautée.")
        return None

    # 2. Historique
    pattern = f"{DOSSIER_PRINCIPAL}/**/{code_ligue}.csv"
    fichiers = glob.glob(pattern, recursive=True)
    
    all_data = []
    for f in fichiers:
        try:
            try: df = pd.read_csv(f, on_bad_lines='skip')
            except: df = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
            df = standardiser_colonnes(df)
            if 'FTHG' in df.columns and 'FTAG' in df.columns:
                df = df[['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']].dropna()
                df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce')
                df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce')
                all_data.append(df)
        except: pass

    if not all_data: return None

    df_global = pd.concat(all_data, ignore_index=True)
    df_global['TotalButs'] = df_global['FTHG'] + df_global['FTAG']
    df_global['IsOver1.5'] = df_global['TotalButs'] > 1.5

    pct_global = (df_global['IsOver1.5'].sum() / len(df_global)) * 100

    resultats = []
    for equipe in equipes_actuelles:
        matchs_eq = df_global[(df_global['HomeTeam'] == equipe) | (df_global['AwayTeam'] == equipe)]
        nb_joues = len(matchs_eq)
        if nb_joues > 0:
            nb_over = matchs_eq['IsOver1.5'].sum()
            pct = (nb_over / nb_joues) * 100
            resultats.append({'Équipe': equipe, '% Over 1.5': pct, 'Matchs': nb_joues})

    df_final = pd.DataFrame(resultats)
    if not df_final.empty:
        df_final = df_final.sort_values(by='% Over 1.5', ascending=False).reset_index(drop=True)
        
    return {'df': df_final, 'pct_global': pct_global}

def generer_html_multi(resultats_par_ligue):
    """Génère le HTML avec menu déroulant."""
    
    # Création des options du menu
    options_html = ""
    sections_html = ""
    
    first = True
    for code, nom in LIGUES_A_ANALYSER.items():
        if code not in resultats_par_ligue: continue
        
        data = resultats_par_ligue[code]
        df = data['df']
        pct_glob = data['pct_global']
        
        # Option du menu
        options_html += f'<option value="{code}">{nom}</option>'
        
        # Section HTML (Tableau)
        display_style = "block" if first else "none"
        first = False
        
        rows_html = ""
        for i, row in df.iterrows():
            pct = row['% Over 1.5']
            diff = pct - pct_glob
            diff_class = "diff-pos" if diff >= 0 else "diff-neg"
            diff_sign = "+" if diff > 0 else ""
            rank = "🏆" if i == 0 else str(i+1)
            
            rows_html += f"""
            <tr>
                <td class="rank">{rank}</td>
                <td class="team">{row['Équipe']}</td>
                <td class="pct">{pct:.2f}%</td>
                <td class="matchs">{row['Matchs']}</td>
                <td class="{diff_class}">{diff_sign}{diff:.2f}%</td>
            </tr>
            """

        sections_html += f"""
        <div id="section-{code}" class="league-section" style="display: {display_style};">
            <div class="stats-box">
                Moyenne historique <strong>{nom}</strong> : <strong>{pct_glob:.2f}%</strong> de matchs +1.5 buts
            </div>
            <table>
                <thead>
                    <tr><th style="text-align:center">#</th><th>Équipe</th><th>% Réussite</th><th>Matchs</th><th>Écart / Moy.</th></tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Analyse Over 1.5 Multi-Ligues</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h1 {{ text-align: center; color: #2c3e50; margin-top: 0; }}
            
            select {{ width: 100%; padding: 15px; font-size: 1.1em; border: 2px solid #ddd; border-radius: 8px; margin-bottom: 20px; background: #fff; cursor: pointer; }}
            select:focus {{ border-color: #3498db; outline: none; }}
            
            .stats-box {{ background-color: #e8f4f8; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px; border-left: 5px solid #3498db; color: #2c3e50; }}
            
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background-color: #34495e; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
            tr:hover {{ background-color: #f8f9fa; }}
            
            .rank {{ font-weight: bold; color: #7f8c8d; text-align: center; width: 40px; }}
            .team {{ font-weight: 600; }}
            .pct {{ font-weight: bold; color: #27ae60; }}
            .diff-pos {{ color: #27ae60; font-weight: bold; font-size: 0.9em; }}
            .diff-neg {{ color: #c0392b; font-weight: bold; font-size: 0.9em; }}
            
            tr:nth-child(1) td {{ background-color: #fff9c4; }}
        </style>
        <script>
            function changeLeague(selectObject) {{
                var value = selectObject.value;
                var sections = document.getElementsByClassName('league-section');
                for (var i = 0; i < sections.length; i++) {{
                    sections[i].style.display = 'none';
                }}
                document.getElementById('section-' + value).style.display = 'block';
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>⚽ Historique Over 1.5 Buts</h1>
            
            <select onchange="changeLeague(this)">
                {options_html}
            </select>
            
            {sections_html}
        </div>
    </body>
    </html>
    """
    
    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\n✨ Rapport généré : {os.path.abspath(FICHIER_SORTIE)}")

def main():
    data_global = {}
    
    for code, nom in LIGUES_A_ANALYSER.items():
        res = analyser_ligue(code, nom)
        if res:
            data_global[code] = res
            
    if data_global:
        generer_html_multi(data_global)
    else:
        print("❌ Aucune donnée trouvée pour les ligues demandées.")

if __name__ == "__main__":
    main()