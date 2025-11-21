import pandas as pd
import glob
import os

# --- CONFIGURATION ---
DOSSIER_PRINCIPAL = "CSV_Data"
DOSSIER_SAISON_ACTUELLE = "data2025" 
FICHIER_SORTIE = "rapport_strategies_mentales.html"

def standardiser_colonnes(df):
    mapping = {
        'Home': 'HomeTeam', 'Home Team': 'HomeTeam',
        'Away': 'AwayTeam', 'Away Team': 'AwayTeam',
        'Res': 'FTR', 'Result': 'FTR', 'FTR': 'FTR',
        'HG': 'FTHG', 'FTHG': 'FTHG', 'HomeGoals': 'FTHG',
        'AG': 'FTAG', 'FTAG': 'FTAG', 'AwayGoals': 'FTAG',
        'HTHG': 'HTHG', 'HTAG': 'HTAG',
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
    print(f"✅ {len(equipes)} équipes actives identifiées.")
    return list(equipes)

def generer_html(df_wtn, df_bot):
    """Génère le rapport HTML avec deux tableaux."""
    
    # --- Construction des lignes pour le tableau WIN TO NIL ---
    rows_wtn = ""
    for i, row in df_wtn.iterrows():
        rows_wtn += f"""
        <tr>
            <td class="rank">{i+1}</td>
            <td class="league">{row['Ligue']}</td>
            <td class="team">{row['Équipe']}</td>
            <td class="pct-green">{row['% WinToNil']:.1f}%</td>
            <td class="details">{row['Nb']} matchs sur {row['Total']}</td>
        </tr>
        """

    # --- Construction des lignes pour le tableau BOTTLERS ---
    rows_bot = ""
    for i, row in df_bot.iterrows():
        rows_bot += f"""
        <tr>
            <td class="rank">{i+1}</td>
            <td class="league">{row['Ligue']}</td>
            <td class="team">{row['Équipe']}</td>
            <td class="pct-red">{row['% Bottle']:.1f}%</td>
            <td class="details">A raté {row['Nb Fail']} fois (sur {row['Mene MT']} leads)</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Analyse Stratégies Avancées</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f7f6; padding: 30px; color: #333; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            h1 {{ text-align: center; color: #2c3e50; margin-bottom: 40px; }}
            
            .section {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 40px; }}
            
            h2 {{ margin-top: 0; font-size: 1.5em; display: flex; align-items: center; gap: 10px; }}
            .title-wtn {{ color: #27ae60; border-bottom: 3px solid #27ae60; padding-bottom: 10px; }}
            .title-bot {{ color: #c0392b; border-bottom: 3px solid #c0392b; padding-bottom: 10px; }}
            
            .desc {{ color: #7f8c8d; font-style: italic; margin-bottom: 20px; }}

            table {{ width: 100%; border-collapse: collapse; }}
            th {{ text-align: left; padding: 12px 15px; background-color: #f8f9fa; color: #555; font-weight: 600; }}
            td {{ padding: 12px 15px; border-bottom: 1px solid #eee; }}
            tr:hover {{ background-color: #fafafa; }}

            .rank {{ font-weight: bold; color: #bbb; width: 30px; }}
            .league {{ font-size: 0.85em; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px; }}
            .team {{ font-weight: 700; font-size: 1.05em; }}
            .details {{ font-size: 0.9em; color: #666; }}
            
            .pct-green {{ font-weight: bold; color: #27ae60; font-size: 1.1em; }}
            .pct-red {{ font-weight: bold; color: #c0392b; font-size: 1.1em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 Analyse Comportementale (Historique)</h1>

            <div class="section">
                <h2 class="title-wtn">🛡️ Les "Forteresses" (Win to Nil)</h2>
                <p class="desc">Équipes qui gagnent le plus souvent <strong>sans encaisser de but</strong>. Idéal pour les paris "Vainqueur sans encaisser" ou "Score exact multi-choix".</p>
                <table>
                    <thead><tr><th>#</th><th>Ligue</th><th>Équipe</th><th>% Réussite</th><th>Historique</th></tr></thead>
                    <tbody>
                        {rows_wtn}
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2 class="title-bot">🤬 Les "Bottlers" (Fragiles)</h2>
                <p class="desc">Équipes qui <strong>ne gagnent pas</strong> le match alors qu'elles <strong>menaient à la mi-temps</strong>. Idéal pour le Live Betting (Double chance X2 à la mi-temps).</p>
                <table>
                    <thead><tr><th>#</th><th>Ligue</th><th>Équipe</th><th>% d'Échec</th><th>Détails</th></tr></thead>
                    <tbody>
                        {rows_bot}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """

    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✨ Rapport généré : {os.path.abspath(FICHIER_SORTIE)}")


def analyser_strategies_historique():
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
            cols_req = ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HTHG', 'HTAG', 'FTR']
            
            if all(c in df.columns for c in cols_req):
                df = df[cols_req].dropna()
                for c in ['FTHG', 'FTAG', 'HTHG', 'HTAG']:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
                df['Ligue'] = os.path.basename(f).replace('.csv', '')
                all_data.append(df)
        except: pass

    if not all_data:
        print("❌ Aucune donnée trouvée.")
        return

    df_global = pd.concat(all_data, ignore_index=True)
    
    res_wtn = []
    res_bottlers = []

    for eq in equipes_actives:
        d = df_global[(df_global['HomeTeam'] == eq) | (df_global['AwayTeam'] == eq)]
        nb_joues = len(d)
        if nb_joues < 20: continue 
        
        derniere_ligue = d.iloc[-1]['Ligue'] if not d.empty else "?"

        # --- A. WIN TO NIL ---
        wtn_home = d[(d['HomeTeam'] == eq) & (d['FTR'] == 'H') & (d['FTAG'] == 0)]
        wtn_away = d[(d['AwayTeam'] == eq) & (d['FTR'] == 'A') & (d['FTHG'] == 0)]
        nb_wtn = len(wtn_home) + len(wtn_away)
        pct_wtn = (nb_wtn / nb_joues) * 100
        
        if pct_wtn > 25: # Seuil d'affichage
            res_wtn.append({'Équipe': eq, 'Ligue': derniere_ligue, '% WinToNil': pct_wtn, 'Nb': nb_wtn, 'Total': nb_joues})

        # --- B. BOTTLERS ---
        mene_mt_home = d[(d['HomeTeam'] == eq) & (d['HTHG'] > d['HTAG'])]
        mene_mt_away = d[(d['AwayTeam'] == eq) & (d['HTAG'] > d['HTHG'])]
        total_mene_mt = len(mene_mt_home) + len(mene_mt_away)
        
        # Matchs où elle menait MAIS n'a pas gagné (D ou A si home, D ou H si away)
        fail_home = mene_mt_home[mene_mt_home['FTR'] != 'H']
        fail_away = mene_mt_away[mene_mt_away['FTR'] != 'A']
        nb_fail = len(fail_home) + len(fail_away)
        
        if total_mene_mt >= 10: 
            pct_bottle = (nb_fail / total_mene_mt) * 100
            if pct_bottle > 20: # Seuil d'affichage
                res_bottlers.append({'Équipe': eq, 'Ligue': derniere_ligue, '% Bottle': pct_bottle, 'Nb Fail': nb_fail, 'Mene MT': total_mene_mt})

    # Tri et HTML
    df_wtn = pd.DataFrame(res_wtn).sort_values('% WinToNil', ascending=False).head(30)
    df_bot = pd.DataFrame(res_bottlers).sort_values('% Bottle', ascending=False).head(30)

    generer_html(df_wtn, df_bot)

if __name__ == "__main__":
    analyser_strategies_historique()