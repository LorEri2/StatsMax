import pandas as pd
import glob
import os

# --- CONFIGURATION ---
DOSSIER_PRINCIPAL = "CSV_Data"
DOSSIER_SAISON_ACTUELLE = "data2025" 
FICHIER_SORTIE = "rapport_safe_bets.html"
SEUIL_POURCENTAGE = 75.0 # On ne montre que ce qui arrive > 75% du temps

def standardiser_colonnes(df):
    mapping = {
        'Home': 'HomeTeam', 'Home Team': 'HomeTeam',
        'Away': 'AwayTeam', 'Away Team': 'AwayTeam',
        'Res': 'FTR', 'Result': 'FTR', 'FTR': 'FTR',
        'HG': 'FTHG', 'FTHG': 'FTHG', 'HomeGoals': 'FTHG',
        'AG': 'FTAG', 'FTAG': 'FTAG', 'AwayGoals': 'FTAG',
        'Date': 'Date'
    }
    return df.rename(columns=mapping)

def get_equipes_actuelles():
    print(f"🔍 Identification des équipes de la saison {DOSSIER_SAISON_ACTUELLE}...")
    path = os.path.join(DOSSIER_PRINCIPAL, DOSSIER_SAISON_ACTUELLE, "*.csv")
    files = glob.glob(path)
    equipes = set()
    for f in files:
        try:
            try: df = pd.read_csv(f, on_bad_lines='skip')
            except: df = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
            df = standardiser_colonnes(df)
            equipes.update(df['HomeTeam'].dropna().unique())
            equipes.update(df['AwayTeam'].dropna().unique())
        except: pass
    return list(equipes)

def generer_html(df_score, df_no_loss, df_over):
    """Génère un rapport avec 3 sections de stats sûres"""
    
    def make_rows(df, col_pct):
        rows = ""
        for i, row in df.iterrows():
            rows += f"""
            <tr>
                <td class="rank">{i+1}</td>
                <td class="league">{row['Ligue']}</td>
                <td class="team">{row['Équipe']}</td>
                <td class="pct">{row[col_pct]:.1f}%</td>
                <td class="details">{row['Succès']}/{row['Total']} matchs</td>
            </tr>
            """
        return rows

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Analyse Safe Bets (>75%)</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background-color: #f0f2f5; padding: 20px; color: #333; }}
            .container {{ max-width: 1100px; margin: 0 auto; }}
            h1 {{ text-align: center; color: #2c3e50; }}
            .subtitle {{ text-align: center; color: #7f8c8d; margin-bottom: 40px; }}
            
            .section {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 40px; }}
            h2 {{ border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 0; }}
            
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #34495e; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #eee; }}
            tr:hover {{ background: #f8f9fa; }}
            
            .rank {{ font-weight: bold; color: #bbb; width: 30px; }}
            .team {{ font-weight: 600; }}
            .pct {{ font-weight: bold; color: #27ae60; font-size: 1.1em; }}
            .league {{ font-size: 0.85em; color: #7f8c8d; text-transform: uppercase; }}
            
            .card-header-score {{ color: #2980b9; border-color: #2980b9; }}
            .card-header-noloss {{ color: #8e44ad; border-color: #8e44ad; }}
            .card-header-over {{ color: #e67e22; border-color: #e67e22; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Les "Safe Bets" (Hautes Fréquences)</h1>
            <p class="subtitle">Statistiques historiques basées sur les équipes actuelles (Seuil: {SEUIL_POURCENTAGE}%)</p>

            <div class="section">
                <h2 class="card-header-score" style="border-bottom: 3px solid #2980b9;">⚽ La Machine à Buts (Marque > 0.5)</h2>
                <p>Équipes qui marquent au moins un but dans presque tous leurs matchs.</p>
                <table>
                    <thead><tr><th>#</th><th>Ligue</th><th>Équipe</th><th>% Marque</th><th>Historique</th></tr></thead>
                    <tbody>{make_rows(df_score, '% Marque')}</tbody>
                </table>
            </div>

            <div class="section">
                <h2 class="card-header-noloss" style="border-bottom: 3px solid #8e44ad;">🛡️ L'Invincible (Ne perd pas / 1X2)</h2>
                <p>Équipes qui font très rarement une défaite (Victoire ou Nul).</p>
                <table>
                    <thead><tr><th>#</th><th>Ligue</th><th>Équipe</th><th>% Invaincu</th><th>Historique</th></tr></thead>
                    <tbody>{make_rows(df_no_loss, '% Invaincu')}</tbody>
                </table>
            </div>

            <div class="section">
                <h2 class="card-header-over" style="border-bottom: 3px solid #e67e22;">🔥 Le Match Ouvert (Over 1.5 Global)</h2>
                <p>Matchs de cette équipe où il y a au moins 2 buts (peu importe qui marque).</p>
                <table>
                    <thead><tr><th>#</th><th>Ligue</th><th>Équipe</th><th>% +1.5 Buts</th><th>Historique</th></tr></thead>
                    <tbody>{make_rows(df_over, '% Over 1.5')}</tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✨ Rapport généré : {os.path.abspath(FICHIER_SORTIE)}")

def analyser_historique():
    print(f"📚 Chargement de l'historique...")
    equipes_actives = get_equipes_actuelles()
    if not equipes_actives: return

    fichiers = glob.glob(f"{DOSSIER_PRINCIPAL}/**/*.csv", recursive=True)
    all_data = []

    for f in fichiers:
        if "fixtures.csv" in f: continue
        try:
            try: df = pd.read_csv(f, on_bad_lines='skip')
            except: df = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
            df = standardiser_colonnes(df)
            
            cols_req = ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
            if all(c in df.columns for c in cols_req):
                df = df[cols_req].dropna()
                for c in ['FTHG', 'FTAG']: df[c] = pd.to_numeric(df[c], errors='coerce')
                df['Ligue'] = os.path.basename(f).replace('.csv', '')
                all_data.append(df)
        except: pass

    if not all_data: print("❌ Aucune donnée."); return
    df_global = pd.concat(all_data, ignore_index=True)
    
    res_score = []
    res_noloss = []
    res_over = []

    for eq in equipes_actives:
        # Matchs de l'équipe
        d = df_global[(df_global['HomeTeam'] == eq) | (df_global['AwayTeam'] == eq)]
        nb = len(d)
        if nb < 20: continue # Minimum 20 matchs pour être fiable
        
        ligue = d.iloc[-1]['Ligue']

        # 1. MARQUE UN BUT (Score > 0)
        # Domicile et marque OU Extérieur et marque
        matchs_avec_but = d[((d['HomeTeam'] == eq) & (d['FTHG'] > 0)) | ((d['AwayTeam'] == eq) & (d['FTAG'] > 0))]
        pct_score = (len(matchs_avec_but) / nb) * 100
        if pct_score >= SEUIL_POURCENTAGE:
            res_score.append({'Équipe': eq, 'Ligue': ligue, '% Marque': pct_score, 'Succès': len(matchs_avec_but), 'Total': nb})

        # 2. NE PERD PAS (Double Chance)
        # Domicile et Pas A (donc H ou D) OU Extérieur et Pas H (donc A ou D)
        matchs_no_loss = d[((d['HomeTeam'] == eq) & (d['FTR'] != 'A')) | ((d['AwayTeam'] == eq) & (d['FTR'] != 'H'))]
        pct_noloss = (len(matchs_no_loss) / nb) * 100
        if pct_noloss >= SEUIL_POURCENTAGE:
             res_noloss.append({'Équipe': eq, 'Ligue': ligue, '% Invaincu': pct_noloss, 'Succès': len(matchs_no_loss), 'Total': nb})

        # 3. OVER 1.5
        matchs_over = d[(d['FTHG'] + d['FTAG']) > 1.5]
        pct_over = (len(matchs_over) / nb) * 100
        if pct_over >= SEUIL_POURCENTAGE:
            res_over.append({'Équipe': eq, 'Ligue': ligue, '% Over 1.5': pct_over, 'Succès': len(matchs_over), 'Total': nb})

    # Tri et Génération
    df_score = pd.DataFrame(res_score).sort_values('% Marque', ascending=False).head(50)
    df_noloss = pd.DataFrame(res_noloss).sort_values('% Invaincu', ascending=False).head(50)
    df_over = pd.DataFrame(res_over).sort_values('% Over 1.5', ascending=False).head(50)

    generer_html(df_score, df_noloss, df_over)

if __name__ == "__main__":
    analyser_historique()