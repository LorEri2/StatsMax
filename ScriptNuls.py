import pandas as pd
import glob
import os
import datetime

# --- 1. CONFIGURATION DES LIGUES ---
LIGUES_A_ANALYSER = {
    # --- Europe Principale ---
    'E0': '🇬🇧 Premier League', 'E1': '🇬🇧 Championship',
    'D1': '🇩🇪 Bundesliga', 'D2': '🇩🇪 Bundesliga 2',
    'F1': '🇫🇷 Ligue 1', 'F2': '🇫🇷 Ligue 2',
    'I1': '🇮🇹 Serie A', 'I2': '🇮🇹 Serie B',
    'SP1': '🇪🇸 La Liga', 'SP2': '🇪🇸 La Liga 2',
    'N1': '🇳🇱 Eredivisie', 'P1': '🇵🇹 Liga Portugal',
    'B1': '🇧🇪 Jupiler Pro League', 'SC0': '🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scottish Premiership',
    'T1': '🇹🇷 Süper Lig', 'G1': '🇬🇷 Super League',

    # --- Reste du Monde ---
    'ARG': '🇦🇷 Argentine', 'AUT': '🇦🇹 Autriche',
    'BRA': '🇧🇷 Brésil', 'CHN': '🇨🇳 Chine',
    'DNK': '🇩🇰 Danemark', 'FIN': '🇫🇮 Finlande',
    'IRL': '🇮🇪 Irlande', 'JPN': '🇯🇵 Japon',
    'MEX': '🇲🇽 Mexique', 'NOR': '🇳🇴 Norvège',
    'POL': '🇵🇱 Pologne', 'ROU': '🇷🇴 Roumanie',
    'RUS': '🇷🇺 Russie', 'SWE': '🇸🇪 Suède',
    'SWZ': '🇨🇭 Suisse', 'USA': '🇺🇸 MLS (USA)'
}

DOSSIER_PRINCIPAL = "CSV_Data"
SAISON_ACTUELLE_DOSSIER = "data2025" 
FICHIER_SORTIE = "rapport_nuls_toutes_ligues.html"

def standardiser_colonnes(df):
    """
    Permet de lire à la fois les fichiers classiques et les nouveaux.
    Pour les nuls, on a besoin de 'FTR' (Result) ou 'Res'.
    """
    mapping = {
        'Home': 'HomeTeam', 'Home Team': 'HomeTeam', 'Team1': 'HomeTeam',
        'Away': 'AwayTeam', 'Away Team': 'AwayTeam', 'Team2': 'AwayTeam',
        'Res': 'FTR', 'Result': 'FTR', 'FTR': 'FTR',
        'Date': 'Date', 'Match Date': 'Date'
    }
    return df.rename(columns=mapping)

def get_current_teams(dossier_base, ligue_code):
    """Récupère les équipes de la saison actuelle pour filtrer."""
    chemin_actuel = os.path.join(dossier_base, SAISON_ACTUELLE_DOSSIER, f"{ligue_code}.csv")
    
    if not os.path.exists(chemin_actuel):
        return None
    
    try:
        try: df = pd.read_csv(chemin_actuel, on_bad_lines='skip')
        except: df = pd.read_csv(chemin_actuel, on_bad_lines='skip', encoding='latin1')
        
        df = standardiser_colonnes(df)
        equipes = set(df['HomeTeam'].dropna().unique()) | set(df['AwayTeam'].dropna().unique())
        return list(equipes)
    except:
        return None

def analyser_ligue(code_ligue, nom_ligue):
    print(f"Traitement Nuls : {nom_ligue} ({code_ligue})...")
    
    equipes_actuelles = get_current_teams(DOSSIER_PRINCIPAL, code_ligue)
    
    pattern = f"{DOSSIER_PRINCIPAL}/**/{code_ligue}.csv"
    fichiers = glob.glob(pattern, recursive=True)
    
    if not fichiers:
        return None

    all_data = []
    for f in fichiers:
        try:
            try: df = pd.read_csv(f, on_bad_lines='skip')
            except: df = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
            
            df = standardiser_colonnes(df)
            
            # On a besoin du résultat final (FTR) pour calculer les nuls
            if 'FTR' in df.columns:
                df = df[['HomeTeam', 'AwayTeam', 'FTR']].dropna()
                # On remplace les éventuels NaN par "NA" pour éviter les bugs
                df['FTR'] = df['FTR'].fillna('NA')
                all_data.append(df)
        except: pass

    if not all_data: return None

    # Fusionner tout l'historique
    df_global = pd.concat(all_data, ignore_index=True)
    
    # Calculer la stat NUL (FTR == 'D')
    df_global['IsDraw'] = df_global['FTR'] == 'D'

    if len(df_global) == 0: return None
    pct_global = (df_global['IsDraw'].sum() / len(df_global)) * 100

    if not equipes_actuelles:
        equipes_actuelles = list(set(df_global['HomeTeam'].unique()) | set(df_global['AwayTeam'].unique()))

    # Calculer les stats par équipe
    resultats = []
    for equipe in equipes_actuelles:
        matchs_eq = df_global[(df_global['HomeTeam'] == equipe) | (df_global['AwayTeam'] == equipe)]
        nb_joues = len(matchs_eq)
        
        if nb_joues > 10:
            nb_nuls = matchs_eq['IsDraw'].sum()
            pct = (nb_nuls / nb_joues) * 100
            resultats.append({
                'Équipe': equipe, 
                '% Nuls': pct, 
                'Matchs': nb_joues
            })

    df_final = pd.DataFrame(resultats)
    if not df_final.empty:
        df_final = df_final.sort_values(by='% Nuls', ascending=False).reset_index(drop=True)
        
    return {'df': df_final, 'pct_global': pct_global}

def generer_html(data_global):
    options_html = '<option value="" disabled selected>-- Choisir une Ligue --</option>'
    sections_html = ""
    
    sorted_ligues = sorted(LIGUES_A_ANALYSER.items(), key=lambda x: x[1])
    
    for code, nom in sorted_ligues:
        if code not in data_global: continue
        
        ligue_data = data_global[code]
        df = ligue_data['df']
        pct_glob = ligue_data['pct_global']
        
        options_html += f'<option value="{code}">{nom}</option>'
        
        rows_html = ""
        for i, row in df.iterrows():
            pct = row['% Nuls']
            diff = pct - pct_glob
            diff_class = "diff-pos" if diff >= 0 else "diff-neg"
            diff_str = f"+{diff:.1f}%" if diff > 0 else f"{diff:.1f}%"
            rank = "🏆" if i == 0 else str(i+1)
            
            rows_html += f"""
            <tr>
                <td class="rank">{rank}</td>
                <td class="team">{row['Équipe']}</td>
                <td class="pct">{pct:.1f}%</td>
                <td class="matchs">{row['Matchs']}</td>
                <td class="{diff_class}">{diff_str}</td>
            </tr>
            """
            
        sections_html += f"""
        <div id="section-{code}" class="league-section" style="display: none;">
            <div class="header-box">
                <h2>{nom}</h2>
                <div class="global-stat">
                    Moyenne historique : <strong>{pct_glob:.1f}%</strong> de matchs nuls
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th width="50">#</th>
                        <th>Équipe</th>
                        <th>% Nuls</th>
                        <th>Historique</th>
                        <th>/ Moyenne</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Analyse Matchs Nuls - Toutes Ligues</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; padding: 20px; color: #333; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #2c3e50; }}
            
            select {{ width: 100%; padding: 15px; font-size: 16px; border-radius: 8px; border: 2px solid #ddd; margin-bottom: 20px; cursor: pointer; }}
            select:focus {{ border-color: #f39c12; outline: none; }}
            
            /* Couleur Orange pour les Nuls */
            .header-box {{ text-align: center; margin-bottom: 20px; background: #fff3e0; padding: 15px; border-radius: 8px; color: #e65100; border-left: 5px solid #f39c12; }}
            .header-box h2 {{ margin: 0 0 5px 0; }}
            
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #34495e; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
            tr:hover {{ background: #f8f9fa; }}
            
            .rank {{ font-weight: bold; color: #7f8c8d; text-align: center; }}
            .team {{ font-weight: 600; }}
            .pct {{ font-weight: bold; color: #e67e22; font-size: 1.1em; }} /* Orange */
            .matchs {{ font-size: 0.9em; color: #666; }}
            .diff-pos {{ color: #27ae60; font-weight: bold; font-size: 0.9em; }}
            .diff-neg {{ color: #c0392b; font-weight: bold; font-size: 0.9em; }}
            
            tr:nth-child(1) td {{ background-color: #fff9c4; }}
        </style>
        <script>
            function changeLeague(select) {{
                var sections = document.getElementsByClassName('league-section');
                for(var i=0; i<sections.length; i++) sections[i].style.display = 'none';
                var selected = document.getElementById('section-' + select.value);
                if(selected) selected.style.display = 'block';
            }}
            window.onload = function() {{
                var select = document.querySelector('select');
                if(select.options.length > 1) {{
                    select.selectedIndex = 1; 
                    changeLeague(select);
                }}
            }};
        </script>
    </head>
    <body>
        <div class="container">
            <h1>⚖️ Analyse Matchs Nuls</h1>
            <select onchange="changeLeague(this)">
                {options_html}
            </select>
            {sections_html}
        </div>
    </body>
    </html>
    """
    
    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✨ Rapport généré : {os.path.abspath(FICHIER_SORTIE)}")

def main():
    print("--- Démarrage de l'analyse Multi-Ligues Matchs Nuls ---")
    data_global = {}
    
    for code, nom in LIGUES_A_ANALYSER.items():
        res = analyser_ligue(code, nom)
        if res:
            data_global[code] = res
            
    if data_global:
        generer_html(data_global)
    else:
        print("❌ Aucune donnée trouvée.")

if __name__ == "__main__":
    main()