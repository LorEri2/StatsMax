import pandas as pd
import numpy as np
import glob 
import os   
import re   
import requests 
import config   
import time     
import datetime
import json     
import warnings

# =============================================================================
# 1. CONFIGURATION & MAPPINGS
# =============================================================================

LEAGUE_NAME_MAPPING = {
    'E0': 'Premier League', 'E1': 'Championship', 'D1': 'Bundesliga',
    'D2': 'Bundesliga 2', 'F1': 'Ligue 1', 'F2': 'Ligue 2',
    'I1': 'Serie A', 'I2': 'Serie B', 'SP1': 'La Liga',
    'SP2': 'La Liga 2', 'N1': 'Eredivisie', 'P1': 'Liga Portugal',
    'T1': 'Süper Lig', 'G1': 'Super League (Grèce)', 'SC0': 'Scottish Premiership',
    'B1': 'Jupiler Pro League', 'ARG': 'Argentine', 'AUT': 'Autriche', 'BRA': 'Brésil',
    'CHN': 'Chine', 'DNK': 'Danemark', 'FIN': 'Finlande', 'IRL': 'Irlande',
    'JPN': 'Japon', 'MEX': 'Mexique', 'NOR': 'Norvège', 'POL': 'Pologne',
    'ROU': 'Roumanie', 'RUS': 'Russie', 'SWE': 'Suède', 'SWZ': 'Suisse', 'USA': 'MLS'
}

ODDS_API_LEAGUE_MAP = {
    'E0': 'soccer_epl', 'E1': 'soccer_england_championship',
    'D1': 'soccer_germany_bundesliga', 'D2': 'soccer_germany_bundesliga_2',
    'F1': 'soccer_france_ligue_1', 'F2': 'soccer_france_ligue_2',
    'I1': 'soccer_italy_serie_a', 'I2': 'soccer_italy_serie_b',
    'SP1': 'soccer_spain_la_liga', 'SP2': 'soccer_spain_la_liga_2',
    'N1': 'soccer_netherlands_eredivisie', 'P1': 'soccer_portugal_primeira_liga',
    'SC0': 'soccer_scotland_premiership', 'B1': 'soccer_belgium_first_div',
    'T1': 'soccer_turkey_super_league', 'G1': 'soccer_greece_super_league_1',
    'ARG': 'soccer_argentina_primera_division', 'AUT': 'soccer_austria_bundesliga',
    'BRA': 'soccer_brazil_campeonato', 'CHN': 'soccer_china_superleague',
    'DNK': 'soccer_denmark_superliga', 'FIN': 'soccer_finland_veikkausliiga',
    'IRL': 'soccer_ireland_premier_division', 'JPN': 'soccer_japan_j_league',
    'MEX': 'soccer_mexico_ligamx', 'NOR': 'soccer_norway_eliteserien',
    'POL': 'soccer_poland_ekstraklasa', 'SWE': 'soccer_sweden_allsvenskan',
    'SWZ': 'soccer_switzerland_superleague', 'USA': 'soccer_usa_mls'
}

STAT_TO_ODD_COLUMN_MAP = {
    'FT +1.5': 'API_Under_1_5', 'FT +2.5': 'API_Under_2_5', 'FT -2.5': 'API_Over_2_5',
    'FT CS': 'API_BTTS_Yes', 'FT No CS': 'API_BTTS_No'
}

STATS_COLUMNS_BASE = [
    'FT Marque', 'FT CS', 'FT No CS', 'FT -0.5', 'FT +1.5', 'FT -1.5', 'FT +2.5', 
    'FT -2.5', 'FT +3.5', 'FT -3.5', 'FT Nuls', 'MT +0.5', 'MT -0.5'
]

# =============================================================================
# 2. CONTENU HTML/CSS/JS GLOBAL
# =============================================================================

CSS_GLOBAL = """
<style>
    html { scroll-behavior: smooth; } body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 0; }
    .app-header { background-color: #1a1a1a; color: white; padding: 15px 20px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2); position: sticky; top: 0; z-index: 1000; }
    .app-header h1 { margin: 0 0 15px 0; font-size: 1.5em; }
    .mode-switcher { display: flex; justify-content: center; gap: 20px; }
    .mode-btn { padding: 10px 25px; border: none; border-radius: 30px; font-size: 1.1em; font-weight: bold; cursor: pointer; transition: all 0.3s; text-transform: uppercase; opacity: 0.7; }
    .mode-btn:hover { opacity: 1; transform: translateY(-2px); }
    .mode-btn.active { opacity: 1; box-shadow: 0 0 10px rgba(255,255,255,0.5); }
    .btn-statsmax { background-color: #007bff; color: white; }
    .btn-over15 { background-color: #28a745; color: white; }
    .sub-nav { background-color: #333; padding: 10px; display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; position: sticky; top: 85px; z-index: 999; }
    .sub-nav a { color: #ccc; text-decoration: none; font-size: 0.85em; padding: 6px 12px; border-radius: 4px; transition: background 0.2s; cursor: pointer; }
    .sub-nav a:hover { background-color: #555; color: white; } .sub-nav a.active { background-color: #555; color: white; border-bottom: 3px solid #007bff; }
    .alert-button { border-left: 3px solid #ffc107; } .pre-alert-button { border-left: 3px solid #f57c00; }
    .broken-button { border-left: 3px solid #dc3545; } .dashboard-button { border-left: 3px solid #007bff; }
    .main-content { padding: 20px; max-width: 1200px; margin: 0 auto; }
    .app-section { display: none; animation: fadeIn 0.5s; } .app-section.active { display: block; }
    .tab-content { display: none; } .tab-content.active { display: block; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    .league-filter-container { margin-bottom: 20px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    #league-filter { width: 100%; padding: 10px; font-size: 1em; border-radius: 5px; border: 1px solid #ddd; }
    .styled-table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 30px; }
    .styled-table thead { background-color: #333; color: white; }
    .styled-table th, .styled-table td { padding: 12px 15px; text-align: center; border-bottom: 1px solid #eee; }
    .styled-table th { cursor: pointer; } .styled-table th:first-child, .styled-table td:first-child { text-align: left; }
    .styled-table tbody tr:hover { background-color: #f5f5f5; }
    .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
    .dashboard-card { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .card-value { font-size: 2.5em; font-weight: bold; margin: 10px 0; }
    .card-red .card-value { color: #c82333; } .form-pill { display: inline-block; width: 20px; height: 20px; line-height: 20px; text-align: center; border-radius: 4px; color: white; font-size: 0.75em; margin: 0 1px; }
    .form-v { background: #28a745; } .form-n { background: #ffc107; color: #333; } .form-d { background: #dc3545; }
    .section-title { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }
    .alerts-table td:nth-child(9) { font-weight: bold; color: #0056b3; }
</style>
"""

JS_GLOBAL = """
<script>
    const formPillMapping = {'V': '<span class="form-pill form-v">V</span>', 'N': '<span class="form-pill form-n">N</span>', 'D': '<span class="form-pill form-d">D</span>'};
    function switchMode(mode) {
        document.querySelectorAll('.app-section').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.mode-btn').forEach(el => el.classList.remove('active'));
        document.getElementById('section-' + mode).classList.add('active');
        document.getElementById('btn-' + mode).classList.add('active');
        if (mode === 'statsmax') {
            const activeTab = document.querySelector('.tab-content.active');
            if (!activeTab) showSection('dashboard-section');
        }
    }
    function showSection(sectionId, clickedLink) {
        document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
        document.getElementById(sectionId).classList.add('active');
        if (clickedLink) {
            document.querySelectorAll('.sub-nav a').forEach(el => el.classList.remove('active'));
            clickedLink.classList.add('active');
        }
    }
    function filterTablesByLeague(selectedLeague) {
        document.querySelectorAll('.filterable-table').forEach(table => {
            let colIndex = table.classList.contains('last-week-table') ? 1 : 0;
            table.querySelectorAll('tbody tr').forEach(row => {
                const cell = row.querySelectorAll('td')[colIndex];
                if (cell) row.style.display = (selectedLeague === 'Toutes' || cell.innerText === selectedLeague) ? '' : 'none';
            });
        });
    }
    function makeTablesSortable() {
        document.querySelectorAll("th").forEach((th, idx) => {
            th.addEventListener("click", () => {
                const table = th.closest("table");
                const tbody = table.querySelector("tbody");
                const rows = Array.from(tbody.querySelectorAll("tr"));
                const isAsc = th.getAttribute("data-dir") === "asc";
                rows.sort((a, b) => {
                    const valA = a.cells[idx].innerText.replace(/[^0-9.-]/g, '');
                    const valB = b.cells[idx].innerText.replace(/[^0-9.-]/g, '');
                    const numA = parseFloat(valA); const numB = parseFloat(valB);
                    if (!isNaN(numA) && !isNaN(numB)) return isAsc ? numA - numB : numB - numA;
                    return isAsc ? a.cells[idx].innerText.localeCompare(b.cells[idx].innerText) : b.cells[idx].innerText.localeCompare(a.cells[idx].innerText);
                });
                tbody.innerHTML = ""; rows.forEach(row => tbody.appendChild(row));
                th.setAttribute("data-dir", isAsc ? "desc" : "asc");
            });
        });
    }
    function formatFormString(formStr) { if (!formStr || formStr === "N/A") return "N/A"; return formStr.split(',').map(r => formPillMapping[r.trim()] || r).join(' '); }
    function populateTeamSelector(selectedLeague) {
        const teamSelector = document.getElementById('team-selector');
        teamSelector.innerHTML = '<option value="">-- Choisissez une équipe --</option>';
        if (!selectedLeague) { teamSelector.disabled = true; return; }
        const teamData = JSON.parse(document.getElementById('team-data-json').textContent);
        let teams = [];
        for (const t in teamData) { if (teamData[t].Ligue === selectedLeague) teams.push(t); }
        teams.sort().forEach(t => teamSelector.innerHTML += `<option value="${t}">${t}</option>`);
        teamSelector.disabled = false;
    }
    function showTeamStats(teamName) {
        const cont = document.getElementById('team-details-container');
        if (!teamName) { cont.innerHTML = ""; return; }
        const data = JSON.parse(document.getElementById('team-data-json').textContent)[teamName];
        let html = `<h3>${teamName} (${data.Ligue})</h3><table class="styled-table">`;
        html += `<tr><td>Prochain</td><td>${data.Prochain_Match || 'N/A'}</td></tr>`;
        html += `<tr><td>Forme</td><td>${data.Form_Score ? data.Form_Score.toFixed(1) : '0'}</td></tr>`;
        html += `<tr><td>Détails</td><td>${formatFormString(data.Form_Last_5_Str)}</td></tr>`;
        for (const key in data) {
            if (key.endsWith('_Record')) {
                const base = key.replace('_Record', '');
                const rec = data[key]; const curr = data[base + '_EnCours']; const pct = data[base + '_Pct']; const yr = data[base + '_Annee_Record'];
                html += `<tr><td>${base}</td><td>Rec: <strong>${rec}</strong> (${yr}) | Sér: <strong>${curr}</strong> | ${pct ? pct.toFixed(1)+'%' : ''}</td></tr>`;
            }
        }
        html += "</table>"; cont.innerHTML = html;
    }
    document.addEventListener("DOMContentLoaded", () => { makeTablesSortable(); switchMode('statsmax'); });
</script>
"""

# =============================================================================
# 3. FONCTIONS HELPER
# =============================================================================

def standardiser_colonnes(df):
    mapping = {
        'Home': 'HomeTeam', 'Home Team': 'HomeTeam', 'Team1': 'HomeTeam',
        'Away': 'AwayTeam', 'Away Team': 'AwayTeam', 'Team2': 'AwayTeam',
        'Match Date': 'Date', 'MatchDate': 'Date', 'DT': 'Date',
        'HG': 'FTHG', 'HomeGoals': 'FTHG', 'FTHG': 'FTHG',
        'AG': 'FTAG', 'AwayGoals': 'FTAG', 'FTAG': 'FTAG',
        'Res': 'FTR', 'Result': 'FTR', 'FTR': 'FTR',
        'B36CA': 'B365CA'
    }
    return df.rename(columns=mapping)

def formater_forme_html(forme_string):
    if pd.isna(forme_string) or forme_string == "N/A" or not forme_string: return "N/A"
    mapping = {'V': '<span class="form-pill form-v">V</span>', 'N': '<span class="form-pill form-n">N</span>', 'D': '<span class="form-pill form-d">D</span>'}
    pills = [mapping.get(resultat.strip(), resultat) for resultat in forme_string.split(',')]
    return " ".join(pills)

def trouver_max_serie_pour_colonne(df_equipe, nom_colonne_condition):
    if nom_colonne_condition not in df_equipe.columns or 'Date' not in df_equipe.columns: return 0, "N/A"
    df_equipe = df_equipe.sort_values(by='Date')
    df_equipe['streak_group'] = (df_equipe[nom_colonne_condition] != df_equipe[nom_colonne_condition].shift()).cumsum()
    streaks_when_true = df_equipe[df_equipe[nom_colonne_condition] == True]
    if streaks_when_true.empty: return 0, "N/A"
    streak_lengths = streaks_when_true.groupby('streak_group').size()
    max_streak = int(streak_lengths.max())
    groupes_max = streak_lengths[streak_lengths == max_streak].index
    dates_possibles = streaks_when_true[streaks_when_true['streak_group'].isin(groupes_max)]['Date']
    last_date = dates_possibles.max()
    return max_streak, last_date.year

def trouver_serie_en_cours_pour_colonne(df_equipe, nom_colonne_condition):
    if nom_colonne_condition not in df_equipe.columns: return 0 
    df_equipe = df_equipe.sort_values(by='Date')
    conditions_list = df_equipe[nom_colonne_condition].tolist()
    serie_en_cours = 0
    for condition_remplie in reversed(conditions_list):
        if condition_remplie: serie_en_cours += 1
        else: break
    return serie_en_cours

def calculer_pourcentage_reussite(df_equipe, nom_colonne_condition):
    if nom_colonne_condition not in df_equipe.columns or df_equipe.empty: return 0.0
    return (df_equipe[nom_colonne_condition].sum() / len(df_equipe)) * 100

def calculer_score_de_forme(df_equipe, equipe):
    if 'FTR' not in df_equipe.columns or 'FTHG' not in df_equipe.columns: return 0, "N/A"
    df_equipe_forme = df_equipe[~df_equipe['FTR'].isna() & (df_equipe['FTR'] != 'NA')].copy().sort_values(by='Date')
    last_5 = df_equipe_forme.tail(5)
    if len(last_5) < 5: return 0, "Pas assez de matchs"
    scores = []; details = []; weights = [0.2, 0.4, 0.6, 0.8, 1.0]; idx = 0
    for _, match in last_5.iterrows():
        s = 0; res = match['FTR']
        is_home = match['HomeTeam'] == equipe
        if (is_home and res == 'H') or (not is_home and res == 'A'): s += 5; r = "V"
        elif res == 'D': s += 1; r = "N"
        else: s -= 3; r = "D"
        hg = match['FTHG']; ag = match['FTAG']
        my_goals = hg if is_home else ag
        opp_goals = ag if is_home else hg
        if my_goals >= 3: s += 2
        if opp_goals == 0: s += 2
        scores.append(s * weights[idx]); idx += 1; details.append(r)
    return sum(scores), ", ".join(reversed(details))

def analyser_cache_series(df_actuel, df_cache):
    print("Comparaison avec le cache...")
    if df_cache.empty: return pd.DataFrame(columns=['Ligue', 'Équipe', 'Statistique', 'Série Précédente']), 0, 0
    try:
        df_merged = pd.merge(df_actuel, df_cache, on=['Ligue', 'Équipe'], suffixes=('_actuel', '_cache'), how='left')
        brisees = []; actives_encore = []
        for stat in STATS_COLUMNS_BASE:
            col_actuel = f'{stat}_EnCours_actuel'; col_cache = f'{stat}_EnCours_cache'
            if col_actuel not in df_merged.columns or col_cache not in df_merged.columns: continue
            df_merged[col_cache] = df_merged[col_cache].fillna(0)
            condition_brisee = (df_merged[col_cache] > 0) & (df_merged[col_actuel] == 0)
            for _, row in df_merged[condition_brisee].iterrows():
                brisees.append({'Ligue': row['Ligue'], 'Équipe': row['Équipe'], 'Statistique': stat, 'Série Précédente': int(row[col_cache])})
            condition_active = (df_merged[col_cache] > 0) & (df_merged[col_actuel] > 0)
            actives_encore.extend(df_merged[condition_active].to_dict('records'))
        
        df_final_brisees = pd.DataFrame(brisees)
        if not df_final_brisees.empty:
            df_final_brisees = df_final_brisees.sort_values(by=['Ligue', 'Équipe', 'Série Précédente'], ascending=[True, True, False])
        return df_final_brisees, len(brisees), len(actives_encore)
    except Exception as e:
        print(f"Erreur cache: {e}"); return pd.DataFrame(columns=['Ligue', 'Équipe', 'Statistique', 'Série Précédente']), 0, 0

def envoyer_notifications_discord(alertes_rouges, webhook_url):
    if not alertes_rouges: return
    print(f"Envoi de {len(alertes_rouges)} notifications vers Discord...")
    message_description = ""
    for alerte in alertes_rouges:
        message_description += f"**{alerte['Équipe']}** ({alerte['Ligue']}) : **{alerte['Statistique']}** (Série: **{alerte['Série en Cours']}**)\n"
    if len(message_description) > 1900: message_description = message_description[:1900] + "\n... et plus encore."
    data = { "content": f"🚨 **{len(alertes_rouges)} Alertes Rouges Détectées !** 🚨", "embeds": [ { "title": "Rapport des Séries au Record", "description": message_description, "color": 15158332, "footer": { "text": f"Analyse effectuée le {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}" } } ] }
    try:
        requests.post(webhook_url, json=data)
        print("  - Notifications Discord envoyées.")
    except Exception as e:
        print(f"  - ERREUR Discord: {e}")

def calculer_stats_over15_historique(df):
    print("Calcul de l'historique Over 1.5...")
    df['TotalGoals'] = pd.to_numeric(df['FTHG'], errors='coerce') + pd.to_numeric(df['FTAG'], errors='coerce')
    df['IsOver15'] = df['TotalGoals'] > 1.5
    stats_list = []
    equipes = sorted(list(set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())))
    for eq in equipes:
        d = df[(df['HomeTeam'] == eq) | (df['AwayTeam'] == eq)]
        nb = len(d)
        if nb < 20: continue
        nb_over = d['IsOver15'].sum()
        pct = (nb_over / nb) * 100
        derniere_ligue = d.iloc[-1]['LeagueCode'] if not d.empty else 'X0'
        nom_ligue = LEAGUE_NAME_MAPPING.get(derniere_ligue, derniere_ligue)
        stats_list.append({'Ligue': nom_ligue, 'Équipe': eq, 'Matchs Joués': nb, 'Over 1.5': nb_over, '% Over 1.5': pct})
    df_ov = pd.DataFrame(stats_list)
    if not df_ov.empty: df_ov = df_ov.sort_values('% Over 1.5', ascending=False)
    return df_ov

# --- Styles ---
def colorier_series_v19(row):
    rec = row['Record']; curr = row['Série en Cours']
    base = ['font-weight: normal; color: #777; text-align: left;', '', '', 'text-align: center;', 'font-weight: normal; color: #555;', 'font-weight: bold; color: #333; text-align: center;', 'color: #777; font-size: 0.9em;']
    if curr > 0 and curr == rec: base[4] = 'background-color: #ffebee; color: #c62828; font-weight: bold;'
    elif curr > 0 and curr == rec - 1: base[4] = 'background-color: #fff3e0; color: #f57c00; font-weight: bold;'
    elif curr > 0 and curr == rec - 2: base[4] = 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    return base

def colorier_tableau_alertes_v22(row):
    alt = row['Alerte']; s = ''
    if alt == 'Rouge': s = 'background-color: #ffebee; color: #c62828; font-weight: bold;'
    elif alt == 'Orange': s = 'background-color: #fff3e0; color: #f57c00; font-weight: bold;'
    elif alt == 'Vert': s = 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    return [s + 'text-align: left; font-weight: normal; color: #333;', s, s, s, s+'text-align:center; font-weight: normal;', s, s+'font-weight: normal; font-size: 0.9em;', s+'color: #17a2b8; font-weight: normal;', s+'color: #0056b3; text-align: center;', s]

def colorier_forme_v22(row):
    sc = row['Score de Forme']; s = ''
    if sc > 10: s = 'color: #2e7d32; font-weight: bold;'
    elif sc > 0: s = 'color: #28a745;'
    elif sc < -5: s = 'color: #c62828; font-weight: bold;'
    elif sc < 0: s = 'color: #dc3545;'
    return ['text-align: left;', '', s, '', 'color: #17a2b8;']

# =============================================================================
# 4. CHARGEMENT ET CALCULS
# =============================================================================

def charger_donnees_robuste(fichiers_csv):
    all_dfs = []
    print(f"Chargement de {len(fichiers_csv)} fichiers...")
    for f in fichiers_csv:
        try:
            try: df = pd.read_csv(f, on_bad_lines='skip')
            except: df = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
            df = standardiser_colonnes(df)
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                df['Date_Parsable'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
                if df['Date_Parsable'].isna().mean() > 0.8: 
                    df['Date_Parsable'] = pd.to_datetime(df['Date'], dayfirst=False, errors='coerce')
            
            df['Date'] = df['Date_Parsable']
            df = df.dropna(subset=['Date'])
            if df.empty: continue
            df['LeagueCode'] = os.path.basename(f).replace('.csv', '')
            all_dfs.append(df)
        except Exception as e: print(f"Erreur fichier {f}: {e}")
    if not all_dfs: return None
    df_final = pd.concat(all_dfs, ignore_index=True)
    df_final = df_final.dropna(subset=['HomeTeam', 'AwayTeam'])
    df_final = df_final.sort_values(by='Date')
    for col in ['FTHG', 'FTAG', 'HTHG', 'HTAG']:
        if col in df_final.columns:
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)
    if 'FTR' not in df_final.columns: df_final['FTR'] = 'NA'
    else: df_final['FTR'] = df_final['FTR'].fillna('NA')
    df_final['TotalGoals'] = df_final['FTHG'] + df_final['FTAG']
    if 'HTHG' in df_final.columns: df_final['TotalHTGoals'] = df_final['HTHG'] + df_final['HTAG']
    else: df_final['TotalHTGoals'] = 0
    df_final['Cond_Moins_0_5_FT'] = df_final['TotalGoals'] < 0.5; df_final['Cond_Plus_1_5_FT'] = df_final['TotalGoals'] > 1.5
    df_final['Cond_Moins_1_5_FT'] = df_final['TotalGoals'] < 1.5; df_final['Cond_Plus_2_5_FT'] = df_final['TotalGoals'] > 2.5
    df_final['Cond_Moins_2_5_FT'] = df_final['TotalGoals'] < 2.5; df_final['Cond_Plus_3_5_FT'] = df_final['TotalGoals'] > 3.5
    df_final['Cond_Moins_3_5_FT'] = df_final['TotalGoals'] < 3.5; df_final['Cond_Plus_0_5_HT'] = df_final['TotalHTGoals'] > 0.5
    df_final['Cond_Moins_0_5_HT'] = df_final['TotalHTGoals'] < 0.5; df_final['Cond_Plus_1_5_HT'] = df_final['TotalHTGoals'] > 1.5
    df_final['Cond_Moins_1_5_HT'] = df_final['TotalHTGoals'] < 1.5; df_final['Cond_Draw_FT'] = df_final['FTR'] == 'D'
    return df_final

def charger_cotes_via_api(api_key, codes_ligues):
    if not api_key or "VOTRE_CLÉ" in api_key: return {}
    print("Chargement cotes API...")
    sports = [ODDS_API_LEAGUE_MAP[c] for c in codes_ligues if c in ODDS_API_LEAGUE_MAP]
    if not sports: return {}
    final_dict = {}
    try:
        resp = requests.get("https://api.the-odds-api.com/v4/sports/soccer/odds/", params={
            'apiKey': api_key, 'regions': 'eu', 'markets': 'h2h,totals', 'sports': ','.join(sports[:15]), 'oddsFormat': 'decimal', 'bookmakers': 'bet365'
        })
        if resp.status_code == 200:
            for m in resp.json():
                home, away = m.get('home_team'), m.get('away_team')
                if not home: continue
                odds = {}; bookies = m.get('bookmakers', [])
                bk = next((b for b in bookies if b['key'] == 'bet365'), bookies[0] if bookies else None)
                if not bk: continue
                for mk in bk['markets']:
                    k = mk['key']
                    for o in mk['outcomes']:
                        n, p = o['name'], o['price']
                        if k == 'h2h':
                            if n == home: odds['API_H'] = p
                            elif n == away: odds['API_A'] = p
                            else: odds['API_D'] = p
                        elif k == 'totals':
                            pt = o.get('point')
                            if n == 'Over': odds[f'API_Over_{pt}'.replace('.','_')] = p
                            else: odds[f'API_Under_{pt}'.replace('.','_')] = p
                if 'API_H' in odds and 'API_A' in odds: odds['API_12'] = round(1/(1/odds['API_H'] + 1/odds['API_A']), 2)
                info = {'opponent': away, 'loc': 'Home', 'odds': odds, 'commence_time': m.get('commence_time')}
                final_dict[home] = info
                final_dict[away] = {'opponent': home, 'loc': 'Away', 'odds': odds, 'commence_time': m.get('commence_time')}
    except: pass
    return final_dict

def calculer_stats_globales(df, ligues_map, odds_dict):
    res = []
    cols_map = {
        'FT Marque': 'Cond_FT_Score', 'FT CS': 'Cond_FT_CS', 'FT No CS': 'Cond_FT_No_CS',
        'FT -0.5': 'Cond_Moins_0_5_FT', 'FT +1.5': 'Cond_Plus_1_5_FT', 'FT -1.5': 'Cond_Moins_1_5_FT',
        'FT +2.5': 'Cond_Plus_2_5_FT', 'FT -2.5': 'Cond_Moins_2_5_FT', 'FT +3.5': 'Cond_Plus_3_5_FT',
        'FT -3.5': 'Cond_Moins_3_5_FT', 'FT Nuls': 'Cond_Draw_FT', 'MT +0.5': 'Cond_Plus_0_5_HT',
        'MT -0.5': 'Cond_Moins_0_5_HT', 'MT +1.5': 'Cond_Plus_1_5_HT', 'MT -1.5': 'Cond_Moins_1_5_HT'
    }
    print("Calcul des stats...")
    for code, equipes in ligues_map.items():
        nom_ligue = LEAGUE_NAME_MAPPING.get(code, code)
        for eq in equipes:
            d = df[(df['HomeTeam'] == eq) | (df['AwayTeam'] == eq)].copy()
            if d.empty: continue
            d = d.sort_values('Date')
            d['ButsMarques'] = np.where(d['HomeTeam'] == eq, d['FTHG'], d['FTAG'])
            d['ButsEncaisses'] = np.where(d['HomeTeam'] == eq, d['FTAG'], d['FTHG'])
            d['Cond_FT_Score'] = d['ButsMarques'] > 0
            d['Cond_FT_CS'] = d['ButsEncaisses'] == 0
            d['Cond_FT_No_CS'] = d['ButsEncaisses'] > 0
            rec = {'Équipe': eq, 'Ligue': nom_ligue}
            if 'TotalGoals' in d.columns: rec['Last_5_FT_Goals'] = ", ".join(d['TotalGoals'].tail(5).astype(int).astype(str))
            else: rec['Last_5_FT_Goals'] = "N/A"
            if 'TotalHTGoals' in d.columns: rec['Last_5_MT_Goals'] = ", ".join(d['TotalHTGoals'].tail(5).astype(int).astype(str))
            else: rec['Last_5_MT_Goals'] = "N/A"
            sc, det = calculer_score_de_forme(d, eq)
            rec['Form_Score'] = sc; rec['Form_Last_5_Str'] = det
            nxt = "N/A"; info = odds_dict.get(eq)
            if not info:
                for k, v in odds_dict.items():
                    if eq in k or k in eq: info = v; break
            if info:
                try: dt = pd.to_datetime(info['commence_time']).strftime('%d/%m %H:%M')
                except: dt = "?"
                nxt = f"{dt} -> {info['opponent']} ({'Dom' if info['loc']=='Home' else 'Ext'})"
            rec['Prochain_Match'] = nxt
            for stat, col in cols_map.items():
                mx, yr = trouver_max_serie_pour_colonne(d, col)
                cur = trouver_serie_en_cours_pour_colonne(d, col)
                pct = calculer_pourcentage_reussite(d, col)
                rec[f'{stat}_Record'] = mx; rec[f'{stat}_Annee_Record'] = yr
                rec[f'{stat}_EnCours'] = cur; rec[f'{stat}_Pct'] = pct
            res.append(rec)
    return pd.DataFrame(res)

def sauvegarder_rapport_global_html(df, brisees, c_bris, c_act, df_last, df_over15, fichier, titre, odds):
    print("Génération du HTML...")
    rouges = []; pre = []
    for stat in STATS_COLUMNS_BASE:
        col_rec = f'{stat}_Record'; col_cur = f'{stat}_EnCours'; col_yr = f'{stat}_Annee_Record'
        for _, row in df.iterrows():
            r = row[col_rec]; c = row[col_cur]
            if pd.isna(r) or c == 0: continue
            typ = None
            if c == r: typ = 'Rouge'
            elif c == r-1: typ = 'Orange'
            elif c == r-2: typ = 'Vert'
            if typ:
                cote_val = "(Match?)"
                if row['Prochain_Match'] != "N/A":
                    map_key = STAT_TO_ODD_COLUMN_MAP.get(stat)
                    info = odds.get(row['Équipe'])
                    if not info:
                         for k, v in odds.items():
                            if row['Équipe'] in k or k in row['Équipe']: info = v; break
                    if info and map_key:
                        c_api = info['odds'].get(map_key)
                        if c_api: cote_val = str(c_api)
                        else: cote_val = f"({map_key.split('_')[-1]}?)"
                    else: cote_val = "(Stat?)" if not map_key else "(Cote?)"
                item = {
                    'Ligue': row['Ligue'], 'Équipe': row['Équipe'], 'Statistique': stat,
                    'Record': r, 'Année Record': row[col_yr], 'Série en Cours': c,
                    '5 Derniers Buts': row['Last_5_FT_Goals'], 'Prochain Match': row['Prochain_Match'],
                    'Cote (Pari Inverse)': cote_val, 'Alerte': typ
                }
                if typ == 'Rouge': rouges.append(item)
                else: pre.append(item)

    if not rouges: html_rouges = "<h3 class='no-alerts'>Aucune alerte Rouge.</h3>"
    else:
        dfr = pd.DataFrame(rouges).sort_values(['Ligue', 'Équipe'])
        cols = ['Ligue', 'Équipe', 'Statistique', 'Record', 'Année Record', 'Série en Cours', '5 Derniers Buts', 'Prochain Match', 'Cote (Pari Inverse)', 'Alerte']
        html_rouges = dfr[cols].style.apply(colorier_tableau_alertes_v22, axis=1).set_table_attributes('class="styled-table alerts-table filterable-table"').format({'Année Record': '{}'}).hide(axis="index").hide(['Alerte'], axis=1).to_html()

    if not pre: html_pre = "<h3 class='no-alerts'>Aucune pré-alerte.</h3>"
    else:
        dfp = pd.DataFrame(pre)
        dfp['Alerte'] = pd.Categorical(dfp['Alerte'], ["Orange", "Vert"], ordered=True)
        dfp = dfp.sort_values(['Alerte', 'Ligue', 'Équipe'])
        cols = ['Ligue', 'Équipe', 'Statistique', 'Record', 'Année Record', 'Série en Cours', '5 Derniers Buts', 'Prochain Match', 'Cote (Pari Inverse)', 'Alerte']
        html_pre = dfp[cols].style.apply(colorier_tableau_alertes_v22, axis=1).set_table_attributes('class="styled-table alerts-table filterable-table"').format({'Année Record': '{}'}).hide(axis="index").hide(['Alerte'], axis=1).to_html()

    df_forme = df[['Ligue', 'Équipe', 'Form_Score', 'Form_Last_5_Str', 'Prochain_Match']].copy()
    df_forme['5 Derniers (Détails)'] = df_forme['Form_Last_5_Str'].apply(formater_forme_html)
    df_forme = df_forme.sort_values('Form_Score', ascending=False)
    df_forme = df_forme.rename(columns={'Form_Score': 'Score de Forme'})
    df_f_disp = pd.concat([df_forme.head(10), df_forme.tail(10)]).reset_index(drop=True)
    html_forme = df_f_disp[['Ligue', 'Équipe', 'Score de Forme', '5 Derniers (Détails)', 'Prochain_Match']].style.apply(colorier_forme_v22, axis=1).set_table_attributes('class="styled-table form-table filterable-table"').format({'Score de Forme': '{:+.1f}'}).hide(axis="index").to_html()

    if df_last.empty: html_last = "<h3 class='no-alerts'>Aucun match récent.</h3>"
    else:
        dfl = df_last.copy()
        dfl['Date'] = dfl['Date'].dt.strftime('%d/%m')
        dfl['Score'] = dfl['FTHG'].astype(int).astype(str) + ' - ' + dfl['FTAG'].astype(int).astype(str)
        dfl['MT'] = '(' + dfl['HTHG'].astype(int).astype(str) + ' - ' + dfl['HTAG'].astype(int).astype(str) + ')'
        html_last = dfl[['Date', 'Ligue', 'HomeTeam', 'AwayTeam', 'Score', 'MT']].style.set_table_attributes('class="styled-table last-week-table filterable-table"').hide(axis="index").to_html()

    if brisees.empty: html_brisees = "<h3 class='no-alerts'>Aucune série brisée.</h3>"
    else: html_brisees = brisees.style.set_table_attributes('class="styled-table broken-table filterable-table"').hide(axis="index").to_html()

    if df_over15.empty: html_over15 = "<h3 class='no-alerts'>Pas assez de données.</h3>"
    else: html_over15 = df_over15.style.set_table_attributes('class="styled-table filterable-table"').format({'% Over 1.5': '{:.1f}%'}).hide(axis="index").to_html()

    with open(fichier, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>{titre}</title>{CSS_GLOBAL}</head><body>
        <div class="app-header"><h1>ANALYSE FOOTBALL V55</h1><div class="mode-switcher"><button id="btn-statsmax" class="mode-btn btn-statsmax active" onclick="switchMode('statsmax')">📊 STATS MAX</button><button id="btn-over15" class="mode-btn btn-over15" onclick="switchMode('over15')">⚽ HISTO OVER 1.5</button></div></div>
        <div id="section-statsmax" class="app-section active">
            <header class="main-header"><nav class="sub-nav">
                <a href="#" onclick="showSection('dashboard-section', this)" class="dashboard-button active">Tableau de Bord</a>
                <a href="#" onclick="showSection('last-week-section', this)" class="history-button">Résultats Semaine</a>
                <a href="#" onclick="showSection('broken-series-section', this)" class="broken-button">Séries Brisées</a>
                <a href="#" onclick="showSection('team-view-section', this)" class="team-button">Par Équipe</a>
                <a href="#" onclick="showSection('alert-section', this)" class="alert-button">Alertes Rouges</a>
                <a href="#" onclick="showSection('pre-alert-section', this)" class="pre-alert-button">Pré-Alertes</a>
            </nav></header>
            <div class="main-content">
                <div class="league-filter-container" id="league-filter-container">
                    <select id="league-filter" onchange="filterTablesByLeague(this.value)">
                        <option value="Toutes">Toutes les Ligues</option>
                        {''.join([f'<option value="{l}">{l}</option>' for l in sorted(df['Ligue'].unique())])}
                    </select>
                </div>
                <div class="section-container tab-content active" id="dashboard-section">
                    <h2 class="section-title">Tableau de Bord</h2>
                    <div class="dashboard-grid">
                        <div class="dashboard-card card-red"><div class="card-title">Alertes Rouges</div><div class="card-value">{len(rouges)}</div></div>
                        <div class="dashboard-card card-orange"><div class="card-title">Pré-Alertes</div><div class="card-value">{len(pre)}</div></div>
                        <div class="dashboard-card card-broken"><div class="card-title">Brisées</div><div class="card-value">{c_bris}</div></div>
                        <div class="dashboard-card card-api"><div class="card-title">Matchs API</div><div class="card-value">{len(odds)//2}</div></div>
                    </div>
                    <h2 class="section-title">État de Forme (Top/Flop)</h2>{html_forme}
                </div>
                <div class="section-container tab-content" id="last-week-section"><h2 class="section-title">Résultats Semaine</h2>{html_last}</div>
                <div class="section-container tab-content" id="broken-series-section">
                    <h2 class="section-title">Séries Brisées</h2>
                    <div class="broken-summary"><p>Brisées: <strong>{c_bris}</strong> | Actives: <strong>{c_act}</strong></p></div>
                    {html_brisees}
                </div>
                <div class="section-container tab-content" id="team-view-section">
                    <h2 class="section-title">Par Équipe</h2>
                    <select id="league-team-selector" onchange="populateTeamSelector(this.value)">
                        <option value="">-- D'abord, choisir une ligue --</option>
                        {''.join([f'<option value="{l}">{l}</option>' for l in sorted(df['Ligue'].unique())])}
                    </select>
                    <select id="team-selector" onchange="showTeamStats(this.value)" disabled><option>-- Équipe --</option></select>
                    <div id="team-details-container"><div id="team-alerts-output"></div><div id="team-stats-output"></div></div>
                </div>
                <div class="section-container tab-content" id="alert-section"><h2 class="section-title">Alertes Rouges</h2>{html_rouges}</div>
                <div class="section-container tab-content" id="pre-alert-section"><h2 class="section-title">Pré-Alertes</h2>{html_pre}</div>
            </div>
        </div>
        <div id="section-over15" class="app-section">
             <div class="main-content">
                <h2 class="section-title">HISTORIQUE OVER 1.5 BUTS (Toutes Saisons)</h2>
                <div class="league-filter-container" id="league-filter-container-ov">
                    <select onchange="filterTablesByLeague(this.value)">
                        <option value="Toutes">Toutes les Ligues</option>
                        {''.join([f'<option value="{l}">{l}</option>' for l in sorted(df['Ligue'].unique())])}
                    </select>
                </div>
                {html_over15}
             </div>
        </div>
        <script type="application/json" id="team-data-json">{df.set_index('Équipe').to_json(orient='index', force_ascii=False)}</script>
        <script>const STATS_CONFIG = {json.dumps({k:k for k in STATS_COLUMNS_BASE})};</script>
        {JS_GLOBAL}
        </body></html>""")
    print(f"Succès! Rapport généré: {fichier}")

if __name__ == "__main__":
    dossier_csv = "CSV_Data"
    fichier_cache = "rapport_cache.csv"
    csv_files = sorted([f for f in glob.glob(f"{dossier_csv}/**/*.csv", recursive=True) if "fixtures.csv" not in f])
    if not csv_files: print("Erreur: Aucun CSV trouvé."); exit()
    ligues_map = {}
    for f in csv_files:
         code = os.path.basename(f).replace('.csv','')
         try:
             try: dft = pd.read_csv(f, on_bad_lines='skip')
             except: dft = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
             dft = standardiser_colonnes(dft)
             teams = sorted(list(set(dft['HomeTeam'].dropna().unique()) | set(dft['AwayTeam'].dropna().unique())))
             if teams: ligues_map[code] = teams
         except: pass

    df_global = charger_donnees_robuste(csv_files)
    if df_global is None or df_global.empty: exit()
    odds = charger_cotes_via_api(config.API_KEY, ligues_map.keys()) if hasattr(config, 'API_KEY') else {}
    df_res = calculer_stats_globales(df_global, ligues_map, odds)
    print("\n--- RÉSULTATS ---")
    print(df_res.head())
    df_over15 = calculer_stats_over15_historique(df_global)
    df_last = pd.DataFrame()
    if not df_global.empty:
        mx = df_global['Date'].max()
        df_last = df_global[(df_global['Date'] > mx - pd.Timedelta(days=7)) & (df_global['Date'] <= mx)].copy()
        df_last['Ligue'] = df_last['LeagueCode'].map(LEAGUE_NAME_MAPPING).fillna(df_last['LeagueCode'])
    df_cache = pd.DataFrame()
    if os.path.exists(fichier_cache): 
        try: df_cache = pd.read_csv(fichier_cache)
        except: pass
    df_bris, cb, ca = analyser_cache_series(df_res, df_cache)
    if hasattr(config, 'DISCORD_WEBHOOK_URL') and config.DISCORD_WEBHOOK_URL:
        alertes_rouges = []
        for _, row in df_res.iterrows():
            for stat in STATS_COLUMNS_BASE:
                 if row[f'{stat}_EnCours'] > 0 and row[f'{stat}_EnCours'] == row[f'{stat}_Record']:
                     alertes_rouges.append({'Ligue': row['Ligue'], 'Équipe': row['Équipe'], 'Statistique': stat, 'Série en Cours': row[f'{stat}_EnCours']})
        envoyer_notifications_discord(alertes_rouges, config.DISCORD_WEBHOOK_URL)
    sauvegarder_rapport_global_html(df_res, df_bris, cb, ca, df_last, df_over15, "Ft.html", "Rapport V55", odds)
    df_res.to_csv(fichier_cache, index=False)