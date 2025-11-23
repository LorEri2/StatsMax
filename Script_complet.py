import pandas as pd
import numpy as np
import glob
import os
import json
import datetime
import requests # Pour Discord

# ==============================================================================
# CONFIGURATION RAPIDE
# ==============================================================================
DISCORD_WEBHOOK_URL = "" 
DOSSIER_PRINCIPAL_DATA = "CSV_Data" 
LIGUES_A_IGNORER = [] 

# ==============================================================================
# 1. CONFIGURATION & DICTIONNAIRES
# ==============================================================================
LEAGUE_NAME_MAPPING = {
    'epl-2025-GMTStandardTime': 'Premier League', 
    'championship-2025-GMTStandardTime': 'Championship', 
    'bundesliga-2025-UTC': 'Bundesliga',
    'D2': 'Bundesliga 2', #A faire
    'ligue-1-2025-UTC': 'Ligue 1', 
    'F2': 'Ligue 2', # A faire
    'serie-a-2025-UTC': 'Serie A', 
    'I2': 'Serie B', # A faire
    'SP2': 'La Liga 2', # A faire
    'primeira-liga-2025-UTC': 'Liga Portugal',
    'B1': 'Jupiler Pro League',# A faire
    'SC0': 'Scottish Premiership',# A faire
    'super-lig-2025-TurkeyStandardTime': 'Süper Lig',
    'G1': 'Super League (Grèce)',# A faire
    'eredivisie-2025-WEuropeStandardTime': 'Eredivisie',
    'la-liga-2025-UTC': 'La Liga',



}

STATS_COLUMNS_BASE = [
    'FT Marque', 'FT CS', 'FT No CS',
    'FT -0.5', 'FT +1.5', 'FT -1.5', 'FT +2.5', 'FT -2.5', 'FT +3.5', 'FT -3.5', 
    'FT Nuls', 
    'MT +0.5', 'MT -0.5', 'MT +1.5', 'MT -1.5'
]

# ==============================================================================
# 2. CALCULS STATISTIQUES
# ==============================================================================

def trouver_max_serie(df_equipe, col_condition):
    if col_condition not in df_equipe.columns or df_equipe.empty: return 0, "N/A"
    df_equipe = df_equipe.sort_values('Date')
    df_equipe['groupe'] = (df_equipe[col_condition] != df_equipe[col_condition].shift()).cumsum()
    series_true = df_equipe[df_equipe[col_condition] == True]
    if series_true.empty: return 0, "N/A"
    lengths = series_true.groupby('groupe').size()
    max_s = int(lengths.max())
    groupes_max = lengths[lengths == max_s].index
    dates = []
    for g in groupes_max:
        d = series_true[series_true['groupe'] == g]['Date'].max()
        if pd.notna(d): dates.append(d)
    annee = max(dates).year if dates else "N/A"
    return max_s, annee

def trouver_serie_en_cours(df_equipe, col_condition):
    if col_condition not in df_equipe.columns: return 0
    conditions = df_equipe.sort_values('Date')[col_condition].tolist()
    serie = 0
    for c in reversed(conditions):
        if c: serie += 1
        else: break
    return serie

def calculer_pourcentage(df_equipe, col_condition):
    if col_condition not in df_equipe.columns or df_equipe.empty: return 0.0
    return (df_equipe[col_condition].sum() / len(df_equipe)) * 100

def calculer_score_forme(df_equipe, equipe):
    if 'FTR' not in df_equipe.columns: return 0, "N/A"
    df_f = df_equipe[df_equipe['FTR'] != 'NA'].sort_values('Date').tail(5)
    if len(df_f) < 5: return 0, "Pas assez de matchs"
    scores = []
    res_str = []
    ponderations = [0.2, 0.4, 0.6, 0.8, 1.0]
    idx = 0
    for _, row in df_f.iterrows():
        s = 0
        r = row['FTR']
        if (row['HomeTeam'] == equipe and r == 'H') or (row['AwayTeam'] == equipe and r == 'A'):
            s = 5; res_str.append('V')
        elif r == 'D':
            s = 1; res_str.append('N')
        else:
            s = -3; res_str.append('D')
        bm = row['FTHG'] if row['HomeTeam'] == equipe else row['FTAG']
        be = row['FTAG'] if row['HomeTeam'] == equipe else row['FTHG']
        if bm >= 3: s += 2
        if be == 0: s += 2
        scores.append(s * ponderations[idx])
        idx += 1
    return sum(scores), ", ".join(reversed(res_str))

# ==============================================================================
# 3. CHARGEMENT ET NORMALISATION DES DONNÉES
# ==============================================================================

def normaliser_csv_specifique(df):
    """Convertit le format 'Match Number, Result' en format standard 'FTHG, FTAG'."""
    if 'Home Team' in df.columns:
        df.rename(columns={'Home Team': 'HomeTeam', 'Away Team': 'AwayTeam'}, inplace=True)
        
    # 2. Gérer le score "1 - 3" dans la colonne "Result"
    if 'Result' in df.columns:
        # Créer les colonnes si elles n'existent pas
        if 'FTHG' not in df.columns: df['FTHG'] = np.nan
        if 'FTAG' not in df.columns: df['FTAG'] = np.nan
        
        try:
            # On prend les lignes avec score et on fait une copie
            mask_score = df['Result'].notna() & (df['Result'] != '')
            df_score = df.loc[mask_score].copy()
            
            if not df_score.empty:
                split_data = df_score['Result'].str.split(' - ', expand=True)
                if len(split_data.columns) == 2:
                    # On assigne les valeurs converties
                    df.loc[mask_score, 'FTHG'] = pd.to_numeric(split_data[0].str.strip(), errors='coerce')
                    df.loc[mask_score, 'FTAG'] = pd.to_numeric(split_data[1].str.strip(), errors='coerce')
                    
                    # Calculer le FTR
                    conditions = [
                        (df['FTHG'] > df['FTAG']),
                        (df['FTHG'] < df['FTAG'])
                    ]
                    choices = ['H', 'A']
                    df.loc[mask_score, 'FTR'] = np.select(conditions, choices, default='D')
        except Exception as e:
            print(f"Erreur parsing scores: {e}")

    if 'HTHG' not in df.columns: df['HTHG'] = 0
    if 'HTAG' not in df.columns: df['HTAG'] = 0
    
    return df

def charger_tout_depuis_csv(liste_fichiers):
    """Charge tout, fusionne et NETTOIE LES DOUBLONS."""
    
    all_dfs = []
    print(f"Chargement de {len(liste_fichiers)} fichiers...")
    
    # 1. Chargement Brut
    for f in liste_fichiers:
        try:
            df_t = pd.read_csv(f, on_bad_lines='skip')
        except:
            try: df_t = pd.read_csv(f, encoding='latin1', on_bad_lines='skip')
            except: continue
        
        df_t = normaliser_csv_specifique(df_t)
        
        # Date Parsing
        df_t['Date'] = pd.to_datetime(df_t['Date'], dayfirst=True, errors='coerce')
        if df_t['Date'].isna().all():
             df_t = pd.read_csv(f, on_bad_lines='skip')
             df_t = normaliser_csv_specifique(df_t)
             df_t['Date'] = pd.to_datetime(df_t['Date'], dayfirst=False, errors='coerce')
        
        df_t['LeagueCode'] = os.path.basename(f).replace('.csv', '')
        all_dfs.append(df_t)
        
    if not all_dfs: return None, pd.DataFrame()
    
    # 2. Fusion Globale
    df_master = pd.concat(all_dfs, ignore_index=True)
    
    # 3. NETTOYAGE DES DOUBLONS (CRUCIAL)
    # On veut garder la ligne qui a un score (FTHG) si elle existe.
    # On trie : les lignes avec FTHG valide (non NaN) en premier (ou dernier selon le sort)
    # En Pandas, sort_values met les NaN à la fin par défaut.
    # Donc si on garde le 'first', on garde celui qui a un score.
    if 'FTHG' in df_master.columns:
        df_master = df_master.sort_values(by=['Date', 'FTHG'], na_position='last')
    
    # On supprime les doublons basés sur Date + Equipes
    # (Si deux fichiers contiennent le même match, on en garde un seul)
    taille_avant = len(df_master)
    df_master = df_master.drop_duplicates(subset=['Date', 'HomeTeam', 'AwayTeam'], keep='first')
    taille_apres = len(df_master)
    
    if taille_avant > taille_apres:
        print(f"🧹 Nettoyage : {taille_avant - taille_apres} matchs en double supprimés.")

    # 4. Séparation Historique / Futur
    cols_req = ['Date', 'HomeTeam', 'AwayTeam']
    df_master = df_master.dropna(subset=cols_req)
    
    # Un match est "JOUÉ" s'il a un score FTHG (et n'est pas NaN)
    mask_joue = df_master['FTHG'].notna()
    
    df_final_hist = df_master[mask_joue].copy()
    
    # Futur : Pas de score ET date >= aujourd'hui
    df_final_future = df_master[~mask_joue].copy()
    df_final_future = df_final_future[df_final_future['Date'] >= pd.Timestamp.now().normalize()]
    
    # Nettoyage Historique Stats
    for col in ['FTHG', 'FTAG', 'HTHG', 'HTAG']:
        if col in df_final_hist.columns:
            df_final_hist[col] = pd.to_numeric(df_final_hist[col], errors='coerce').fillna(0)
            
    # Booléens
    if 'FTHG' in df_final_hist.columns:
        df_final_hist['TotalGoals'] = df_final_hist['FTHG'] + df_final_hist['FTAG']
        df_final_hist['Cond_Moins_0_5_FT'] = df_final_hist['TotalGoals'] < 0.5
        df_final_hist['Cond_Plus_1_5_FT'] = df_final_hist['TotalGoals'] > 1.5
        df_final_hist['Cond_Moins_1_5_FT'] = df_final_hist['TotalGoals'] < 1.5
        df_final_hist['Cond_Plus_2_5_FT'] = df_final_hist['TotalGoals'] > 2.5
        df_final_hist['Cond_Moins_2_5_FT'] = df_final_hist['TotalGoals'] < 2.5
        df_final_hist['Cond_Plus_3_5_FT'] = df_final_hist['TotalGoals'] > 3.5
        df_final_hist['Cond_Moins_3_5_FT'] = df_final_hist['TotalGoals'] < 3.5
    if 'HTHG' in df_final_hist.columns:
        df_final_hist['TotalHTGoals'] = df_final_hist['HTHG'] + df_final_hist['HTAG']
        df_final_hist['Cond_Plus_0_5_HT'] = df_final_hist['TotalHTGoals'] > 0.5
        df_final_hist['Cond_Moins_0_5_HT'] = df_final_hist['TotalHTGoals'] < 0.5
        df_final_hist['Cond_Plus_1_5_HT'] = df_final_hist['TotalHTGoals'] > 1.5
        df_final_hist['Cond_Moins_1_5_HT'] = df_final_hist['TotalHTGoals'] < 1.5
    if 'FTR' in df_final_hist.columns:
        df_final_hist['FTR'] = df_final_hist['FTR'].fillna('NA')
        df_final_hist['Cond_Draw_FT'] = df_final_hist['FTR'] == 'D'
        
    return df_final_hist.sort_values('Date'), df_final_future.sort_values('Date')

def decouvrir_ligues(dossier):
    fichiers = glob.glob(f"{dossier}/**/*.csv", recursive=True)
    ligues = {}
    print("\nRecherche des fichiers (Filtre activé)...")
    for f in fichiers:
        code = os.path.basename(f).replace('.csv', '')
        
        # FILTRE SUR LE DICTIONNAIRE UTILISATEUR
        if code not in LEAGUE_NAME_MAPPING: 
            continue
            
        if code.lower() == 'fixtures': continue 
        try:
            df = pd.read_csv(f, encoding='latin1', on_bad_lines='skip')
            # Petite pré-lecture
            if 'Home Team' in df.columns: 
                df.rename(columns={'Home Team': 'HomeTeam', 'Away Team': 'AwayTeam'}, inplace=True)
            
            teams = sorted(list(set(df['HomeTeam'].dropna()) | set(df['AwayTeam'].dropna())))
            if teams: 
                ligues[code] = teams
                print(f"  ✅ Ajouté: {code}")
        except: pass
    return ligues, fichiers

def charger_fixtures_externes(dossier):
    """Charge le fichier fixtures.csv global (pour les ligues D2/D3)."""
    fichier = os.path.join(dossier, "fixtures.csv")
    if not os.path.exists(fichier): return pd.DataFrame()
    try:
        df = pd.read_csv(fichier, on_bad_lines='skip')
        df = normaliser_csv_specifique(df)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        if df['Date'].isna().all():
             df = pd.read_csv(fichier, on_bad_lines='skip')
             df = normaliser_csv_specifique(df)
             df['Date'] = pd.to_datetime(df['Date'], dayfirst=False, errors='coerce')
        df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
        df = df[df['Date'] >= pd.Timestamp.now().normalize()]
        return df
    except: return pd.DataFrame()

# ==============================================================================
# 4. ANALYSE HYBRIDE
# ==============================================================================

def analyser_donnees(df, ligues_dict, df_future_embedded, df_fixtures_global):
    resultats = []
    conditions = {
        'FT Marque': 'Cond_FT_Score', 'FT CS': 'Cond_FT_CS', 'FT No CS': 'Cond_FT_No_CS',
        'FT -0.5': 'Cond_Moins_0_5_FT', 'FT +1.5': 'Cond_Plus_1_5_FT',
        'FT -1.5': 'Cond_Moins_1_5_FT', 'FT +2.5': 'Cond_Plus_2_5_FT',
        'FT -2.5': 'Cond_Moins_2_5_FT', 'FT +3.5': 'Cond_Plus_3_5_FT',
        'FT -3.5': 'Cond_Moins_3_5_FT', 'FT Nuls': 'Cond_Draw_FT', 
        'MT +0.5': 'Cond_Plus_0_5_HT', 'MT -0.5': 'Cond_Moins_0_5_HT',
        'MT +1.5': 'Cond_Plus_1_5_HT', 'MT -1.5': 'Cond_Moins_1_5_HT',
    }
    print("\nCalcul des statistiques en cours...")
    for code, equipes in ligues_dict.items():
        nom_ligue = LEAGUE_NAME_MAPPING.get(code, code)
        for eq in equipes:
            df_eq = df[(df['HomeTeam'] == eq) | (df['AwayTeam'] == eq)].copy()
            if df_eq.empty: continue
            rec = {'Équipe': eq, 'Ligue': nom_ligue}
            
            # -- LOGIQUE PROCHAIN MATCH (HYBRIDE) --
            prochain = "Pas de match prévu"
            match_trouve = False
            
            # 1. Chercher dans le fichier de la ligue
            if not df_future_embedded.empty:
                futurs = df_future_embedded[(df_future_embedded['HomeTeam'] == eq) | (df_future_embedded['AwayTeam'] == eq)]
                if not futurs.empty:
                    match = futurs.iloc[0]
                    if match['HomeTeam'] == eq: adv = match['AwayTeam']; cote = "Dom"
                    else: adv = match['HomeTeam']; cote = "Ext"
                    prochain = f"{adv} ({cote}) - {match['Date'].strftime('%d/%m')}"
                    match_trouve = True
            
            # 2. Si pas trouvé, chercher dans fixtures.csv
            if not match_trouve and not df_fixtures_global.empty:
                futurs = df_fixtures_global[(df_fixtures_global['HomeTeam'] == eq) | (df_fixtures_global['AwayTeam'] == eq)]
                if not futurs.empty:
                    match = futurs.iloc[0]
                    if match['HomeTeam'] == eq: adv = match['AwayTeam']; cote = "Dom"
                    else: adv = match['HomeTeam']; cote = "Ext"
                    prochain = f"{adv} ({cote}) - {match['Date'].strftime('%d/%m')}"
            
            rec['Prochain_Match'] = prochain

            score, str_forme = calculer_score_forme(df_eq, eq)
            rec['Form_Score'] = score
            rec['Form_Last_5_Str'] = str_forme
            if 'FTHG' in df_eq.columns:
                df_eq['BM'] = np.where(df_eq['HomeTeam'] == eq, df_eq['FTHG'], df_eq['FTAG'])
                df_eq['BE'] = np.where(df_eq['HomeTeam'] == eq, df_eq['FTAG'], df_eq['FTHG'])
                df_eq['Cond_FT_Score'] = df_eq['BM'] > 0
                df_eq['Cond_FT_CS'] = df_eq['BE'] == 0
                df_eq['Cond_FT_No_CS'] = df_eq['BE'] > 0
                l5 = df_eq['TotalGoals'].tail(5).fillna(0).astype(int).tolist()
                rec['Last_5_FT_Goals'] = ",".join(map(str, l5))
            else: rec['Last_5_FT_Goals'] = ""
            for nom_stat, col in conditions.items():
                if col in df_eq.columns:
                    max_s, annee = trouver_max_serie(df_eq, col)
                    curr_s = trouver_serie_en_cours(df_eq, col)
                    pct = calculer_pourcentage(df_eq, col)
                    rec[f'{nom_stat}_Record'] = max_s
                    rec[f'{nom_stat}_Annee_Record'] = annee
                    rec[f'{nom_stat}_EnCours'] = curr_s
                    rec[f'{nom_stat}_Pct'] = pct
            resultats.append(rec)
    return pd.DataFrame(resultats)

# ==============================================================================
# 5. GÉNÉRATION HTML
# ==============================================================================

def generer_html(df_complet, df_brisees, nom_fichier):
    json_data = df_complet.fillna('').to_json(orient='records')

    stats_config = {
        'FT Marque': 'ft_marque', 'FT CS': 'ft_cs', 'FT No CS': 'ft_no_cs',
        'FT Nuls': 'ft_nuls',
        'FT -0.5': 'ft_m05', 'FT +1.5': 'ft_p15', 'FT -1.5': 'ft_m15',
        'FT +2.5': 'ft_p25', 'FT -2.5': 'ft_m25', 'FT +3.5': 'ft_p35', 'FT -3.5': 'ft_m35',
        'MT +0.5': 'mt_p05', 'MT -0.5': 'mt_m05', 'MT +1.5': 'mt_p15', 'MT -1.5': 'mt_m15'
    }

    alertes_rouges = []
    for stat in stats_config:
        col_rec = f'{stat}_Record'
        col_curr = f'{stat}_EnCours'
        col_an = f'{stat}_Annee_Record'
        if col_rec not in df_complet.columns: continue
        for _, row in df_complet.iterrows():
            rec = row[col_rec]
            curr = row[col_curr]
            if curr > 0 and curr == rec:
                alertes_rouges.append({
                    'Ligue': row['Ligue'], 'Équipe': row['Équipe'], 
                    'Statistique': stat, 'Record': rec, 
                    'Année': row.get(col_an, '-'), 'Série': curr
                })

    def render_table_alertes(data_list):
        if not data_list: return '<div class="empty-state">✅ Aucune alerte rouge.</div>'
        df = pd.DataFrame(data_list).sort_values(['Ligue', 'Équipe'])
        html = '<table class="data-table"><thead><tr><th>Ligue</th><th>Équipe</th><th>Statistique</th><th>Série</th><th>Record</th><th>Type</th></tr></thead><tbody>'
        for _, r in df.iterrows():
            html += f"<tr><td><span class='league-tag'>{r['Ligue']}</span></td><td class='fw-bold'>{r['Équipe']}</td><td>{r['Statistique']}</td><td class='text-center font-mono fw-bold'>{r['Série']}</td><td class='text-center'>{r['Record']} <span class='year-tag'>({r['Année']})</span></td><td class='text-center'><span class='badge badge-rouge'>ROUGE</span></td></tr>"
        html += "</tbody></table>"
        return html

    def render_table_forme(df_in):
        cols = ['Ligue', 'Équipe', 'Form_Score', 'Form_Last_5_Str']
        if any(c not in df_in.columns for c in cols): return ""
        df = df_in[cols].copy().sort_values('Form_Score', ascending=False)
        df_top = pd.concat([df.head(10), df.tail(10)])
        html = '<table class="data-table"><thead><tr><th>Ligue</th><th>Équipe</th><th>Score</th><th>5 Derniers Matchs</th></tr></thead><tbody>'
        for _, r in df_top.iterrows():
            s = r['Form_Score']
            color = "#10b981" if s > 10 else "#ef4444" if s < 0 else "#374151"
            pills = "".join([f"<span class='pill pill-{res.strip().lower()}'>{res.strip()}</span>" for res in r['Form_Last_5_Str'].split(',') if res.strip()])
            html += f"<tr><td><span class='league-tag'>{r['Ligue']}</span></td><td class='fw-bold'>{r['Équipe']}</td><td class='text-center' style='color:{color}; font-weight:bold'>{s:+.1f}</td><td><div class='pill-container'>{pills}</div></td></tr>"
        html += "</tbody></table>"
        return html

    def render_table_stats_tab(df_in, stat_name):
        col_rec = f'{stat_name}_Record'
        if col_rec not in df_in.columns: return ""
        cols = ['Ligue', 'Équipe', col_rec, f'{stat_name}_Annee_Record', f'{stat_name}_EnCours', f'{stat_name}_Pct']
        df = df_in[cols].copy().sort_values(col_rec, ascending=False)
        html = '<table class="data-table filterable"><thead><tr><th>Ligue</th><th>Équipe</th><th>Série En Cours</th><th>Record (Année)</th><th>% Réussite</th></tr></thead><tbody>'
        for _, r in df.iterrows():
            rec = r[col_rec]
            curr = r[f'{stat_name}_EnCours']
            row_cls = "row-alert-red" if curr > 0 and curr == rec else ""
            pct = r[f'{stat_name}_Pct']
            pct_bar = f"<div class='pct-track'><div class='pct-fill' style='width:{pct}%'></div></div><span class='pct-text'>{pct:.1f}%</span>"
            html += f"<tr class='{row_cls}'><td><span class='league-tag'>{r['Ligue']}</span></td><td class='fw-bold'>{r['Équipe']}</td><td class='text-center fw-bold'>{curr}</td><td class='text-center'>{rec} <span class='year-tag'>({r.get(f'{stat_name}_Annee_Record','-')})</span></td><td>{pct_bar}</td></tr>"
        html += "</tbody></table>"
        return html

    navbar_html = '<div class="top-navbar"><div class="nav-scroll">'
    navbar_html += '<div class="nav-item active" onclick="showView(\'view-dashboard\', this)">📊 Tableau de Bord</div>'
    navbar_html += '<div class="nav-item search-btn" onclick="showView(\'view-team-search\', this)">🔍 Recherche Équipe</div>'
    navbar_html += '<div class="nav-item" onclick="showView(\'view-forme\', this)">📈 État de Forme</div>'
    for stat, id_tag in stats_config.items():
        navbar_html += f'<div class="nav-item" onclick="showView(\'view-{id_tag}\', this)">{stat}</div>'
    navbar_html += '</div></div>'

    dashboard_html = f"""
    <div id="view-dashboard" class="view-section active">
        <div class="header"><h1>📊 Tableau de Bord</h1><p>Généré le {datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')}</p></div>
        <div class="kpi-grid">
            <div class="kpi-card kpi-red"><div class="kpi-value">{len(alertes_rouges)}</div><div class="kpi-label">Alertes Rouges</div></div>
            <div class="kpi-card kpi-blue"><div class="kpi-value">{len(df_complet)}</div><div class="kpi-label">Équipes</div></div>
            <div class="kpi-card kpi-gray"><div class="kpi-value">{len(df_brisees)}</div><div class="kpi-label">Séries Brisées</div></div>
        </div>
        <div class="card"><h2>🚨 Alertes Actives (Série = Record)</h2>{render_table_alertes(alertes_rouges)}</div>
        <div class="card"><h2>📉 Séries Brisées</h2>
        {('<table class="data-table"><thead><tr><th>Ligue</th><th>Équipe</th><th>Stat</th><th>Arrêtée à</th></tr><tbody>' + ''.join([f"<tr><td>{r['Ligue']}</td><td class='fw-bold'>{r['Équipe']}</td><td>{r['Statistique']}</td><td class='text-center text-red fw-bold'>{r['Série Précédente']}</td></tr>" for _, r in df_brisees.iterrows()]) + '</tbody></table>') if not df_brisees.empty else '<div class="empty-state">Aucune.</div>'}
        </div>
    </div>
    """

    search_html = f"""
    <div id="view-team-search" class="view-section" style="display:none;">
        <div class="header"><h1>🔍 Fiche d'Identité Équipe</h1></div>
        <div class="card filter-box">
            <div class="select-group">
                <label>1. Choisir la Ligue</label>
                <select id="sel-league" onchange="updateTeamList()"><option value="">-- Sélectionner --</option></select>
            </div>
            <div class="select-group">
                <label>2. Choisir l'Équipe</label>
                <select id="sel-team" onchange="displayTeamStats()" disabled><option value="">-- En attente --</option></select>
            </div>
        </div>
        <div id="team-result-container"></div>
    </div>
    """

    forme_view_html = f'<div id="view-forme" class="view-section" style="display:none;"><div class="header"><h1>📈 État de Forme</h1></div><div class="card">{render_table_forme(df_complet)}</div></div>'
    stats_views_html = ""
    for stat, id_tag in stats_config.items():
        stats_views_html += f'<div id="view-{id_tag}" class="view-section" style="display:none;"><div class="header"><h1>Statistiques : {stat}</h1></div><div class="card">{render_table_stats_tab(df_complet, stat)}</div></div>'

    css = """
    <style>
        :root { --bg: #f1f5f9; --nav-bg: #1e293b; --card-bg: #ffffff; --primary: #3b82f6; --text: #0f172a; --red: #ef4444; --green: #10b981; --orange: #f97316; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding-top: 60px; }
        .top-navbar { position: fixed; top: 0; left: 0; width: 100%; height: 60px; background: var(--nav-bg); z-index: 1000; display: flex; align-items: center; }
        .nav-scroll { display: flex; overflow-x: auto; height: 100%; width: 100%; padding: 0 10px; scrollbar-width: none; }
        .nav-item { color: #cbd5e1; padding: 0 20px; line-height: 60px; cursor: pointer; white-space: nowrap; font-weight: 600; border-bottom: 4px solid transparent; }
        .nav-item:hover { color: white; background: rgba(255,255,255,0.05); }
        .nav-item.active { color: white; border-bottom-color: var(--primary); background: rgba(255,255,255,0.05); }
        .search-btn { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .container { max-width: 1200px; margin: 30px auto; padding: 0 20px; }
        .card { background: var(--card-bg); border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 25px; }
        .filter-box { display: flex; gap: 20px; align-items: center; background: #fff; border-left: 5px solid var(--primary); }
        .select-group { flex: 1; }
        select { width: 100%; padding: 10px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 1em; outline: none; }
        .team-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px; }
        .team-title h2 { margin: 0; font-size: 1.8em; color: var(--nav-bg); }
        .team-badge { background: var(--nav-bg); color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.8em; }
        .next-match-box { background-color: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; font-size: 1.2em; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }
        .stat-box { border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; background: #f8fafc; }
        .stat-box.alert { background: #fef2f2; border-color: #fecaca; }
        .stat-name { font-size: 0.9em; color: #64748b; margin-bottom: 5px; }
        .stat-val { font-size: 1.4em; font-weight: bold; color: var(--nav-bg); }
        .stat-rec { font-size: 0.85em; color: #94a3b8; }
        .stat-box.alert .stat-val { color: var(--red); }
        .stat-box.alert .stat-name { color: #991b1b; font-weight: bold; }
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .kpi-card { background: white; padding: 20px; border-radius: 10px; text-align: center; border-top: 4px solid #ccc; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .kpi-red { border-color: var(--red); color: var(--red); } .kpi-blue { border-color: var(--primary); color: var(--primary); } .kpi-value { font-size: 2.5em; font-weight: 800; }
        .data-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.95em; }
        .data-table th { text-align: left; padding: 12px; background: #f8fafc; border-bottom: 2px solid #e2e8f0; color: #64748b; }
        .data-table td { padding: 12px; border-bottom: 1px solid #e2e8f0; }
        .badge-rouge { background: #fef2f2; color: var(--red); } .row-alert-red { background: #fef2f2; } .row-alert-red td { color: #991b1b; }
        .pill { display: inline-block; width: 22px; height: 22px; text-align: center; line-height: 22px; border-radius: 4px; color: white; font-size: 0.75em; font-weight: bold; margin-right: 2px; }
        .pill-v { background: var(--green); } .pill-n { background: #fbbf24; color: #78350f; } .pill-d { background: var(--red); }
        .pct-track { width: 80px; height: 6px; background: #e2e8f0; border-radius: 3px; display: inline-block; margin-right: 8px; }
        .pct-fill { height: 100%; background: var(--primary); border-radius: 3px; }
        .header h1 { font-size: 1.8em; margin: 0; color: #334155; } .header p { color: #94a3b8; margin: 5px 0 20px 0; }
        .league-tag { background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; font-weight: 600; color: #475569; }
        .fw-bold { font-weight: 700; } .text-center { text-align: center; } .text-red { color: var(--red); }
    </style>
    """

    js = f"""
    <script>
        const GLOBAL_DATA = {json_data};
        
        function showView(viewId, navItem) {{
            document.querySelectorAll('.view-section').forEach(el => el.style.display = 'none');
            document.getElementById(viewId).style.display = 'block';
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            navItem.classList.add('active');
            window.scrollTo(0, 0);
            if(viewId === 'view-team-search' && document.getElementById('sel-league').options.length <= 1) {{
                populateLeagues();
            }}
        }}

        function populateLeagues() {{
            const leagues = [...new Set(GLOBAL_DATA.map(item => item.Ligue))].sort();
            const sel = document.getElementById('sel-league');
            leagues.forEach(l => {{
                const opt = document.createElement('option');
                opt.value = l; opt.text = l;
                sel.add(opt);
            }});
        }}

        function updateTeamList() {{
            const league = document.getElementById('sel-league').value;
            const teamSel = document.getElementById('sel-team');
            teamSel.innerHTML = '<option value="">-- Sélectionner --</option>';
            if(!league) {{ teamSel.disabled = true; return; }}
            const teams = [...new Set(GLOBAL_DATA.filter(i => i.Ligue === league).map(i => i['Équipe']))].sort();
            teams.forEach(t => {{
                const opt = document.createElement('option');
                opt.value = t; opt.text = t;
                teamSel.add(opt);
            }});
            teamSel.disabled = false;
        }}

        function displayTeamStats() {{
            const teamName = document.getElementById('sel-team').value;
            const container = document.getElementById('team-result-container');
            if(!teamName) {{ container.innerHTML = ''; return; }}

            const teamData = GLOBAL_DATA.find(i => i['Équipe'] === teamName);
            if(!teamData) return;

            let pills = "";
            if(teamData.Form_Last_5_Str) {{
                pills = teamData.Form_Last_5_Str.split(',').map(res => {{
                    let c = res.trim() === 'V' ? 'pill-v' : res.trim() === 'N' ? 'pill-n' : 'pill-d';
                    return `<span class="pill ${{c}}">${{res.trim()}}</span>`;
                }}).join('');
            }}

            let nextMatchHTML = '';
            if(teamData.Prochain_Match && teamData.Prochain_Match !== 'Pas de match prévu' && teamData.Prochain_Match !== 'Calendrier introuvable') {{
                nextMatchHTML = `<div class="next-match-box">⚽ Prochain Match : <strong>${{teamData.Prochain_Match}}</strong></div>`;
            }} else {{
                nextMatchHTML = `<div class="next-match-box" style="background:#f3f4f6; color:#6b7280; border-color:#e5e7eb;">🚫 ${{teamData.Prochain_Match}}</div>`;
            }}

            let html = `<div class="card">
                <div class="team-header">
                    <div class="team-title"><h2>${{teamName}}</h2></div>
                    <div class="team-badge">${{teamData.Ligue}}</div>
                </div>
                ${{nextMatchHTML}}
                <div style="margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                    <strong>Forme :</strong> ${{pills}} <span style="color:#64748b; margin-left:10px;">(Score: ${{teamData.Form_Score.toFixed(1)}})</span>
                </div>
                <div class="stat-grid">`;

            const statKeys = ['FT Marque', 'FT CS', 'FT No CS', 'FT Nuls', 'FT -0.5', 'FT +1.5', 'FT -1.5', 'FT +2.5', 'MT +0.5', 'MT -0.5'];
            statKeys.forEach(stat => {{
                let rec = teamData[stat + '_Record'];
                let curr = teamData[stat + '_EnCours'];
                let an = teamData[stat + '_Annee_Record'] || '-';
                
                if(rec !== undefined) {{
                    let isAlert = (curr > 0 && curr === rec);
                    let cls = isAlert ? 'alert' : '';
                    let icon = isAlert ? '🚨 ' : '';
                    html += `<div class="stat-box ${{cls}}"><div class="stat-name">${{icon}}${{stat}}</div><div class="stat-val">Série : ${{curr}}</div><div class="stat-rec">Record : ${{rec}} (${{an}})</div></div>`;
                }}
            }});
            html += `</div></div>`;
            container.innerHTML = html;
        }}
    </script>
    """

    full_html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Foot Stats Dashboard</title>{css}</head>
    <body>
        {navbar_html}
        <div class="container">
            {dashboard_html}
            {search_html}
            {forme_view_html}
            {stats_views_html}
        </div>
        {js}
    </body></html>"""

    try:
        with open(nom_fichier, 'w', encoding='utf-8') as f: f.write(full_html)
        print(f"\n✨ Rapport HTML généré (V12 Anti-Doublons) : {os.path.abspath(nom_fichier)}")
    except Exception as e: print(f"Erreur HTML: {e}")

# ==============================================================================
# 6. GESTION DU CACHE
# ==============================================================================

def comparer_cache(df_new, fichier_cache):
    if not os.path.exists(fichier_cache): return pd.DataFrame()
    try:
        df_old = pd.read_csv(fichier_cache)
        df_m = pd.merge(df_new, df_old, on=['Ligue', 'Équipe'], suffixes=('_new', '_old'), how='inner')
        brisees = []
        for stat in STATS_COLUMNS_BASE:
            c_new = f'{stat}_EnCours_new'
            c_old = f'{stat}_EnCours_old'
            if c_new in df_m.columns and c_old in df_m.columns:
                mask = (df_m[c_old] > 0) & (df_m[c_new] == 0)
                temp = df_m[mask][['Ligue', 'Équipe', c_old]].copy()
                temp['Statistique'] = stat
                temp = temp.rename(columns={c_old: 'Série Précédente'})
                brisees.append(temp)
        return pd.concat(brisees) if brisees else pd.DataFrame()
    except: return pd.DataFrame()

# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print("--- DÉMARRAGE ANALYSE ---")
    ligues, fichiers = decouvrir_ligues(DOSSIER_PRINCIPAL_DATA)
    if not ligues:
        print(f"ERREUR: Aucun fichier CSV trouvé dans {DOSSIER_PRINCIPAL_DATA}")
        exit()
    
    # 1. Chargement TOUT depuis les fichiers de ligue (Historique + Futurs intégrés + Nettoyage Doublons)
    df_hist, df_fixtures_embedded = charger_tout_depuis_csv(fichiers)
    if df_hist is None: exit()
    
    # 2. Chargement du fichier "fixtures.csv" GLOBAL
    df_fixtures_global = charger_fixtures_externes(DOSSIER_PRINCIPAL_DATA)
    
    # 3. Analyse
    df_resultats = analyser_donnees(df_hist, ligues, df_fixtures_embedded, df_fixtures_global)
    
    CACHE_FILE = "cache_series.csv"
    df_brisees = comparer_cache(df_resultats, CACHE_FILE)
    df_resultats.to_csv(CACHE_FILE, index=False)
    
    generer_html(df_resultats, df_brisees, "index.html")
    
    if DISCORD_WEBHOOK_URL:
        rouges = []
        for stat in STATS_COLUMNS_BASE:
            mask = (df_resultats[f'{stat}_EnCours'] > 0) & (df_resultats[f'{stat}_EnCours'] == df_resultats[f'{stat}_Record'])
            for _, row in df_resultats[mask].iterrows(): rouges.append(f"**{row['Équipe']}** ({row['Ligue']}) : {stat} ({row[f'{stat}_EnCours']})")
        if rouges:
            msg = "🚨 **ALERTES ROUGES** 🚨\n\n" + "\n".join(rouges[:15])
            if len(rouges) > 15: msg += f"\n... +{len(rouges)-15} autres"
            try: requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
            except: pass
    print("\n--- TERMINÉ ---")