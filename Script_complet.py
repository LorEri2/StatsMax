import pandas as pd
import numpy as np
import glob # Pour lire les fichiers dans un dossier
import os   # Pour gérer les noms de fichiers
import re   # Pour les noms de dossiers
import requests # Pour les requêtes API
import config   # Pour charger votre clé
import time     # Pour les pauses API (si nécessaire)
import datetime
import json     # Pour le JS

# ##########################################################################
# --- Dictionnaire de Traduction des Ligues ---
# ##########################################################################
LEAGUE_NAME_MAPPING = {
    'E0': 'Premier League', 'E1': 'Championship', 'D1': 'Bundesliga',
    'D2': 'Bundesliga 2', 'F1': 'Ligue 1', 'F2': 'Ligue 2',
    'I1': 'Serie A', 'I2': 'Serie B', 'SP1': 'La Liga',
    'SP2': 'La Liga 2', 'N1': 'Eredivisie (Pays-Bas)',
    'P1': 'Liga (Portugal)', 'T1': 'Süper Lig (Turquie)',
    'G1': 'Super League (Grèce)', 'SC0': 'Scottish Premiership',
    'B1': 'Jupiler Pro League (Belgique)', 'X0': 'NomParDefaut' 
}

# ##########################################################################
# --- (MODIFIÉ V31) Dictionnaire de Mapping (THE ODDS API) ---
# ##########################################################################
# C'est maintenant notre SEULE source de mapping
ODDS_API_LEAGUE_MAP = {
    'E0': 'soccer_epl',
    'E1': 'soccer_england_championship',
    'D1': 'soccer_germany_bundesliga',
    'D2': 'soccer_germany_bundesliga_2',
    'F1': 'soccer_france_ligue_1',
    'F2': 'soccer_france_ligue_2', # Probablement non couvert par le forfait gratuit
    'I1': 'soccer_italy_serie_a',
    'I2': 'soccer_italy_serie_b', # Probablement non couvert
    'SP1': 'soccer_spain_la_liga',
    'SP2': 'soccer_spain_la_liga_2', # Probablement non couvert
    'N1': 'soccer_netherlands_eredivisie',
    'P1': 'soccer_portugal_primeira_liga',
    'SC0': 'soccer_scotland_premiership',
    'B1': 'soccer_belgium_first_div',
    'T1': 'soccer_turkey_super_league',
    'G1': 'soccer_greece_super_league_1',
}

# ##########################################################################
# --- (MODIFIÉ V30) Dictionnaire de Mapping Cotes/Alertes ---
# ##########################################################################
# ##########################################################################
# --- (MODIFIÉ V31.1) Dictionnaire de Mapping Cotes/Alertes ---
# ##########################################################################
STAT_TO_ODD_COLUMN_MAP = {
    # Alerte sur "Plus de..." -> Parier sur "Moins de..."
    'FT +1.5': 'API_Under_1_5',
    'FT +2.5': 'API_Under_2_5',
    'FT +3.5': 'API_Under_3_5',

    # Alerte sur "Moins de..." -> Parier sur "Plus de..."
    'FT -0.5': 'API_Over_0_5',
    'FT -1.5': 'API_Over_1_5',
    'FT -2.5': 'API_Over_2_5',
    'FT -3.5': 'API_Over_3_5', 

    # Alerte "Clean Sheet" -> Parier sur "Les deux équipes marquent" (BTTS)
    'FT CS': 'API_BTTS_Yes',
    
    # Alerte "Pas de Clean Sheet" -> Parier sur "BTTS Non"
    'FT No CS': 'API_BTTS_No',
    
    # Alerte "Nuls" -> Parier sur "Pas Nul" (12)
    'FT Nuls': 'API_12', # 1 ou 2 gagne
    
    # --- AJOUTS POUR CORRIGER LES (Stat?) ---
    # L'API gratuite ne les fournit PAS, mais au moins le mapping existera.
    'MT +0.5': 'API_MT_Over_0_5',
    'MT -0.5': 'API_MT_Under_0_5',
    'MT +1.5': 'API_MT_Over_1_5',
    'MT -1.5': 'API_MT_Under_1_5',
    'FT Marque': 'API_Team_Under_0_5', # (Nom d'exemple, très difficile à parser)
}
# ##########################################################################
# ##########################################################################


# --- Helper 1: Style pour les 13 tableaux de séries (4 colonnes) ---
def colorier_series_v19(row):
    record = row['Record']
    en_cours = row['Série en Cours']
    style_equipe = '' 
    style_record = '' 
    style_en_cours = 'font-weight: normal; color: #555;' 
    style_5_derniers = 'font-weight: normal; color: #777; font-size: 0.9em;' 
    if en_cours > 0 and en_cours == record:
        style_en_cours = 'background-color: #ffebee; color: #c62828; font-weight: bold;'
    elif en_cours > 0 and en_cours == record - 1:
        style_en_cours = 'background-color: #fff3e0; color: #f57c00; font-weight: bold;'
    elif en_cours > 0 and en_cours == record - 2:
        style_en_cours = 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    return [style_equipe, style_record, style_en_cours, style_5_derniers] 

# --- Helper 2: Style pour le tableau d'alertes (MODIFIÉ V26 pour 8 colonnes) ---
def colorier_tableau_alertes_v22(row):
    alerte_type = row['Alerte']
    style_base = ''
    if alerte_type == 'Rouge':
        style_base = 'background-color: #ffebee; color: #c62828; font-weight: bold;'
    elif alerte_type == 'Orange':
        style_base = 'background-color: #fff3e0; color: #f57c00; font-weight: bold;'
    elif alerte_type == 'Vert':
        style_base = 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    style_5_derniers = style_base + 'font-weight: normal; color: #333; font-size: 0.9em;'
    style_prochain_match = style_base + 'font-weight: normal; color: #17a2b8; font-size: 0.9em;'
    return [style_base, style_base, style_base, style_base, style_5_derniers, style_prochain_match, style_base, style_base]

# --- Helper 3: Style pour le tableau de Forme (4 colonnes) ---
def colorier_forme_v22(row):
    score = row['Score de Forme']
    style_equipe = ''
    style_score = ''
    style_details = 'font-weight: normal; color: #777; font-size: 0.9em;'
    style_prochain_match = 'font-weight: normal; color: #17a2b8; font-size: 0.9em;'
    if score > 10: style_score = 'color: #2e7d32; font-weight: bold;'
    elif score > 0: style_score = 'color: #28a745;'
    elif score < -5: style_score = 'color: #c62828; font-weight: bold;'
    elif score < 0: style_score = 'color: #dc3545;'
    return [style_equipe, style_score, style_details, style_prochain_match]


# --- Helper 4: Génération de la page HTML (MODIFIÉ V30) ---
def sauvegarder_en_html_v22(df_rapport_complet, nom_fichier_html, titre_rapport, odds_api_dict):
    """
    Sauvegarde le DataFrame en 14 onglets + 1 onglet "Alertes" + 1 onglet "Forme".
    MODIFIÉ V30: Utilise 'odds_api_dict' et ajoute un fuzzy matching pour les cotes.
    """
    
    # 1. Définir les 14 statistiques de SÉRIE
    stats_config = {
        'FT Marque': 'FT Marque', 'FT CS': 'FT CS', 'FT No CS': 'FT No CS',
        'FT -0.5': 'FT -0.5', 'FT +1.5': 'FT +1.5', 'FT -1.5': 'FT -1.5',
        'FT +2.5': 'FT +2.5', 'FT -2.5': 'FT -2.5', 'FT +3.5': 'FT +3.5',
        'FT -3.5': 'FT -3.5', 'FT Nuls': 'FT Nuls', 'MT +0.5': 'MT +0.5',
        'MT -0.5': 'MT -0.5', 'MT +1.5': 'MT +1.5', 'MT -1.5': 'MT -1.5',
    }
    
    stats_a_afficher = {
        'FT Marque': ['ft_marque', 'Record - L\'équipe Marque (FT)'],      
        'FT CS': ['ft_cs', 'Record - Clean Sheet (FT)'],            
        'FT No CS': ['ft_no_cs', 'Record - Non Clean Sheet (FT)'],      
        'FT -0.5': ['ft_moins_0_5', 'Record - Fin de Match -0.5 (0 Buts)'],
        'FT +1.5': ['ft_plus_1_5', 'Record - Fin de Match +1.5 (2+ Buts)'],
        'FT -1.5': ['ft_moins_1_5', 'Record - Fin de Match -1.5 (0-1 Buts)'],
        'FT +2.5': ['ft_plus_2_5', 'Record - Fin de Match +2.5 (3+ Buts)'],
        'FT -2.5': ['ft_moins_2_5', 'Record - Fin de Match -2.5 (0-2 Buts)'],
        'FT +3.5': ['ft_plus_3_5', 'Record - Fin de Match +3.5 (4+ Buts)'],
        'FT -3.5': ['ft_moins_3_5', 'Record - Fin de Match -3.5 (0-3 Buts)'],
        'FT Nuls': ['ft_nuls', 'Record - Fin de Match (Nuls)'], 
        'MT +0.5': ['mt_plus_0_5', 'Record - Mi-Temps +0.5 (1+ Buts MT)'],
        'MT -0.5': ['mt_moins_0_5', 'Record - Mi-Temps -0.5 (0 Buts MT)'],
        'MT +1.5': ['mt_plus_1_5', 'Record - Mi-Temps +1.5 (2+ Buts MT)'],
        'MT -1.5': ['mt_moins_1_5', 'Record - Mi-Temps -1.5 (0-1 Buts MT)'],
    }
    
    try:
        # --- 2. Générer la Barre de Navigation (Inchangé) ---
        nav_links = ""
        nav_links += '<a href="#" onclick="showSection(\'team-view-section\', this); event.preventDefault();" class="team-button">🔍 Par Équipe</a>\n'
        nav_links += '<a href="#" onclick="showSection(\'form-section\', this); event.preventDefault();" class="form-button">📈 Forme</a>\n'
        nav_links += '<a href="#" onclick="showSection(\'alert-section\', this); event.preventDefault();" class="alert-button">⚠️ Alertes</a>\n'
        for nom_base, config in stats_a_afficher.items():
            id_html = config[0]
            nav_links += f'<a href="#" onclick="showSection(\'{id_html}\', this); event.preventDefault();">{nom_base}</a>\n'

        # --- 3. Générer le tableau d'alertes (MODIFIÉ V30) ---
        alertes_collectees = []
        for nom_base, config in stats_a_afficher.items():
            col_record = f'{nom_base}_Record'
            col_en_cours = f'{nom_base}_EnCours'
            col_5_derniers = 'Last_5_FT_Goals' if nom_base.startswith('FT') else 'Last_5_MT_Goals'
            
            for index, row in df_rapport_complet.iterrows():
                equipe = row['Équipe'] # Nom CSV (ex: "Dortmund")
                if col_record not in row or pd.isna(row[col_record]): continue
                record = row[col_record]
                en_cours = row[col_en_cours]
                cinq_derniers_str = row.get(col_5_derniers, "N/A")
                prochain_match_str = row.get('Prochain_Match', "N/A")
                
                alerte_type = None
                if en_cours > 0 and en_cours == record: alerte_type = 'Rouge'
                elif en_cours > 0 and en_cours == record - 1: alerte_type = 'Orange'
                elif en_cours > 0 and en_cours == record - 2: alerte_type = 'Vert'
                
                if alerte_type:
                    
                    # --- MODIFIÉ V30 : LOGIQUE DE COTE AVEC FUZZY MATCH ---
                    cote_pari = "N/A"
                    nom_col_cote = STAT_TO_ODD_COLUMN_MAP.get(nom_base)
                    
                    if nom_col_cote:
                        # 1. Essayer un match exact
                        match_info = odds_api_dict.get(equipe)
                        
                        # 2. Essayer un match flou (NomCSV dans NomAPI)
                        if not match_info:
                            for api_nom, api_match_data in odds_api_dict.items():
                                if equipe in api_nom:
                                    match_info = api_match_data
                                    break
                        
                        # 3. Essayer un match flou inversé (NomAPI dans NomCSV)
                        if not match_info:
                            for api_nom, api_match_data in odds_api_dict.items():
                                if api_nom in equipe:
                                    match_info = api_match_data
                                    break

                        # 4. On a trouvé un match, chercher la cote
                        if match_info:
                            cote = match_info['odds'].get(nom_col_cote)
                            if cote: cote_pari = f"{cote:.2f}"
                            else: cote_pari = f"({nom_col_cote.split('_')[-1]}?)" # Affiche (3.5?) (BTTS_Yes?)
                        else: cote_pari = "(Match?)" # Match non trouvé dans l'API de cotes
                    else: cote_pari = "(Stat?)" # Stat non mappée (ex: FT Marque)
                    # --- FIN MODIFICATION V30 ---
                    
                    alertes_collectees.append({
                        'Équipe': equipe, 'Statistique': nom_base, 'Record': record,
                        'Série en Cours': en_cours, '5 Derniers Buts': cinq_derniers_str, 
                        'Prochain Match': prochain_match_str, 'Cote (Pari Inverse)': cote_pari,
                        'Alerte': alerte_type 
                    })

        if not alertes_collectees:
            alert_table_html = "<h3 class='no-alerts'>Aucune alerte active pour le moment.</h3>"
        else:
            df_alertes = pd.DataFrame(alertes_collectees)
            df_alertes['Alerte'] = pd.Categorical(df_alertes['Alerte'], categories=["Rouge", "Orange", "Vert"], ordered=True)
            df_alertes = df_alertes.sort_values(by=['Alerte', 'Équipe']).reset_index(drop=True)
            colonnes_ordre = [
                'Équipe', 'Statistique', 'Record', 'Série en Cours', 
                '5 Derniers Buts', 'Prochain Match', 'Cote (Pari Inverse)', 'Alerte'
            ]
            df_alertes = df_alertes.reindex(columns=colonnes_ordre)
            styler_alertes = df_alertes.style.apply(colorier_tableau_alertes_v22, axis=1) \
                                        .set_table_attributes('class="styled-table alerts-table"') \
                                        .format({'Cote (Pari Inverse)': '{}'}) \
                                        .hide(axis="index") \
                                        .hide(['Alerte'], axis=1) 
            alert_table_html = styler_alertes.to_html()

        # --- 4. Générer le tableau de Forme (Inchangé) ---
        cols_forme = ['Équipe', 'Form_Score', 'Form_Last_5_Str', 'Prochain_Match']
        if 'Form_Score' in df_rapport_complet.columns:
            df_forme = df_rapport_complet[cols_forme].copy()
            df_forme = df_forme.rename(columns={
                'Form_Score': 'Score de Forme',
                'Form_Last_5_Str': '5 Derniers (Détails)',
                'Prochain_Match': 'Prochain Match'
            })
            df_forme = df_forme.sort_values(by='Score de Forme', ascending=False).reset_index(drop=True)
            styler_forme = df_forme.style.apply(colorier_forme_v22, axis=1) \
                                        .set_table_attributes('class="styled-table form-table"') \
                                        .format({'Score de Forme': '{:+.1f}'}) \
                                        .hide(axis="index")
            form_table_html = styler_forme.to_html()
        else:
            form_table_html = "<h3 class='no-alerts'>Données 'FTR' non trouvées pour calculer la forme.</h3>"
        
        # --- 5. Générer le Corps HTML (Onglets de stats - Inchangé) ---
        corps_html = ""
        for nom_base, config in stats_a_afficher.items():
            id_html = config[0]
            titre_section = config[1]
            col_record = f'{nom_base}_Record'
            col_en_cours = f'{nom_base}_EnCours'
            col_5_derniers = 'Last_5_FT_Goals' if nom_base.startswith('FT') else 'Last_5_MT_Goals'
            nom_col_5_derniers = '5 Derniers (FT)' if nom_base.startswith('FT') else '5 Derniers (MT)'
            
            if col_record not in df_rapport_complet.columns:
                print(f"Info: Statistique '{nom_base}' sautée (colonne de données source manquante).")
                continue 
            if col_5_derniers not in df_rapport_complet.columns:
                    df_rapport_complet[col_5_derniers] = "N/A"
            
            df_stat = df_rapport_complet[['Équipe', col_record, col_en_cours, col_5_derniers]].copy()
            df_stat = df_stat.rename(columns={
                col_record: 'Record', col_en_cours: 'Série en Cours',
                col_5_derniers: nom_col_5_derniers
            })
            df_stat = df_stat.sort_values(by='Record', ascending=False).reset_index(drop=True)
            styler = df_stat.style.apply(colorier_series_v19, axis=1) \
                                .set_table_attributes('class="styled-table"') \
                                .hide(axis="index") 
            table_html = styler.to_html()
            corps_html += f"""
            <div class="section-container tab-content" id="{id_html}">
                <h2 class="section-title">{titre_section}</h2>
                {table_html}
            </div>
            """

        # --- 6. Générer la Vue "Par Équipe" (Inchangé) ---
        team_list = sorted(df_rapport_complet['Équipe'].unique())
        team_selector_html = '<select id="team-selector" onchange="showTeamStats(this.value);"><option value="">-- Choisissez une équipe --</option>'
        for team in team_list:
            team_selector_html += f'<option value="{team}">{team}</option>'
        team_selector_html += '</select>'
        team_data_json = df_rapport_complet.set_index('Équipe').to_json(orient="index", force_ascii=False)
        team_view_html = f"""
        <div class="section-container tab-content" id="team-view-section">
            <h2 class="section-title">Analyse par Équipe</h2>
            {team_selector_html}
            <div id="team-details-container">
                <div id="team-alerts-output"></div>
                <div id="team-stats-output"></div>
            </div>
        </div>
        """
        json_data_script = f"""
        <script type="application/json" id="team-data-json">
        {team_data_json}
        </script>
        """
        stats_config_json = json.dumps(stats_config)
        stats_config_script = f"""
        <script>
        const STATS_CONFIG = {stats_config_json};
        </script>
        """

        # --- 7. Définir le Style CSS (Inchangé V29) ---
        html_style = """
        <style>
            html { scroll-behavior: smooth; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f0f2f5; margin: 0; padding: 0;
            }
            .main-header {
                background-color: #222; color: white; padding: 10px 20px;
                font-weight: bold; display: flex; justify-content: space-between;
                align-items: center; position: sticky; top: 0; z-index: 100;
                flex-wrap: wrap; 
            }
            .main-header .logo { font-size: 1.2em; margin-right: 20px; flex-shrink: 0; }
            .main-header nav { display: flex; flex-wrap: wrap; justify-content: center; }
            .main-header nav a {
                color: #ccc; text-decoration: none; margin: 5px; 
                font-size: 0.8em; font-weight: normal; padding: 8px 10px;
                border-radius: 5px; transition: background-color 0.3s, color 0.3s;
            }
            .main-header nav a:hover { background-color: #555; color: white; }
            .main-header nav a.active {
                background-color: #007bff; color: white;
            }
            .main-header nav a.alert-button {
                background-color: #ffc107; color: #333; font-weight: bold;
            }
            .main-header nav a.alert-button.active {
                background-color: #e0a800; color: #000;
            }
            .main-header nav a.form-button {
                background-color: #17a2b8; color: white; font-weight: bold;
            }
            .main-header nav a.form-button.active {
                background-color: #117a8b;
            }
            .main-header nav a.team-button {
                background-color: #6f42c1; color: white; font-weight: bold;
            }
            .main-header nav a.team-button.active {
                background-color: #5a37a0;
            }
            
            .main-content {
                display: flex; justify-content: center; align-items: center;
                flex-direction: column; width: 100%; padding-top: 20px; padding-bottom: 20px;
            }
            .section-container.tab-content {
                display: none; width: 90%; 
                max-width: 1000px;
                margin-bottom: 20px;
            }
            .section-container.tab-content.active { display: block; }
            #welcome-message {
                text-align: center; color: #555;
                font-size: 1.5em; margin-top: 100px;
            }
            .no-alerts {
                text-align: center; color: #555;
                font-size: 1.2em; margin-top: 50px;
            }
            .section-title {
                color: #333; text-align: center; font-size: 1.5em; margin-bottom: 20px;
            }
            .styled-table {
                border-collapse: collapse; width: 100%; 
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                border-radius: 8px; overflow: hidden;
            }
            .styled-table thead tr {
                background-color: #333; color: #ffffff; font-weight: bold;
            }
            .styled-table thead th {
                cursor: pointer;
                user-select: none;
            }
            .styled-table thead th:hover {
                background-color: #555;
            }
            .styled-table thead th.sort-asc::after {
                content: " ▲";
                font-size: 0.8em;
            }
            .styled-table thead th.sort-desc::after {
                content: " ▼";
                font-size: 0.8em;
            }
            
            .styled-table th, .styled-table td { padding: 12px 15px; }
            .styled-table th:nth-child(1), .styled-table td:nth-child(1) { text-align: left; }
            .styled-table th:nth-child(n+2), .styled-table td:nth-child(n+2) {
                text-align: center; font-weight: bold;
            }
            .styled-table th:nth-child(4), .styled-table td:nth-child(4) {
                font-weight: normal; color: #777; font-size: 0.9em;
            }
            .styled-table.form-table th:nth-child(3), .styled-table.form-table td:nth-child(3) {
                font-weight: normal; color: #777; font-size: 0.9em;
            }
            .styled-table.form-table th:nth-child(4), .styled-table.form-table td:nth-child(4) {
                font-weight: normal; color: #17a2b8; font-size: 0.9em;
            }
            .styled-table tbody tr {
                border-bottom: 1px solid #dddddd; background-color: #ffffff;
            }
            .styled-table tbody tr:nth-of-type(even) { background-color: #f8f8f8; }
            .alerts-table td { font-weight: bold !important; }
            .alerts-table td:nth-child(5) { font-weight: normal !important; font-size: 0.9em; }
            .alerts-table td:nth-child(6) { font-weight: normal !important; color: #17a2b8; font-size: 0.9em; }
            .alerts-table td:nth-child(7) { font-weight: bold !important; color: #0056b3; font-size: 1.05em; text-align: center; }
            
            #team-selector {
                width: 100%;
                padding: 12px;
                font-size: 1.1em;
                border-radius: 8px;
                border: 1px solid #ddd;
                margin-bottom: 25px;
                background-color: white;
            }
            #team-alerts-output h3, #team-stats-output h3 {
                color: #333;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
                margin-top: 20px;
            }
            .team-alert-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }
            .team-alert-table th, .team-alert-table td {
                padding: 12px 15px;
                border-bottom: 1px solid #dddddd;
            }
            .team-alert-table th {
                background-color: #333;
                color: white;
                text-align: left;
            }
            .team-alert-table td { font-weight: bold; }
            .team-alert-table tr.Rouge { background-color: #ffebee; color: #c62828; }
            .team-alert-table tr.Orange { background-color: #fff3e0; color: #f57c00; }
            .team-alert-table tr.Vert { background-color: #e8f5e9; color: #2e7d32; }
            
            .team-stats-table {
                width: 100%;
                border-collapse: collapse;
            }
            .team-stats-table th, .team-stats-table td {
                padding: 12px 15px;
                border-bottom: 1px solid #dddddd;
            }
            .team-stats-table tr:nth-of-type(even) { background-color: #f8f8f8; }
            .team-stats-table td:first-child {
                text-align: left;
                color: #555;
                font-weight: normal;
            }
            .team-stats-table td:last-child {
                text-align: right;
                font-weight: bold;
                font-size: 1.05em;
            }
        </style>
        """

        # --- 8. Le SCRIPT JAVASCRIPT (Inchangé V29) ---
        javascript_code = """
        <script>
            function showSection(sectionId, clickedLink) {
                var welcomeMsg = document.getElementById('welcome-message');
                if (welcomeMsg) { welcomeMsg.style.display = 'none'; }
                var sections = document.getElementsByClassName('tab-content');
                for (var i = 0; i < sections.length; i++) {
                    sections[i].classList.remove('active');
                }
                var links = document.querySelectorAll('.main-header nav a');
                for (var i = 0; i < links.length; i++) {
                    links[i].classList.remove('active');
                }
                var activeSection = document.getElementById(sectionId);
                if (activeSection) { activeSection.classList.add('active'); }
                if (clickedLink) { clickedLink.classList.add('active'); }
            }

            function beautifyKey(key) {
                return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            }

            function showTeamStats(teamName) {
                const alertsContainer = document.getElementById('team-alerts-output');
                const statsContainer = document.getElementById('team-stats-output');
                alertsContainer.innerHTML = "";
                statsContainer.innerHTML = "";
                if (!teamName) return;
                const teamData = JSON.parse(document.getElementById('team-data-json').textContent);
                const stats = teamData[teamName];
                if (!stats) {
                    statsContainer.innerHTML = "<p>Erreur : Données non trouvées pour " + teamName + "</p>";
                    return;
                }
                let activeAlerts = [];
                for (const statName in STATS_CONFIG) {
                    const col_en_cours = statName + '_EnCours';
                    const col_record = statName + '_Record';
                    if (stats[col_en_cours] !== undefined && stats[col_record] !== undefined) {
                        const en_cours = stats[col_en_cours];
                        const record = stats[col_record];
                        let alerte_type = null;
                        if (en_cours > 0 && en_cours == record) alerte_type = 'Rouge';
                        else if (en_cours > 0 && en_cours == record - 1) alerte_type = 'Orange';
                        else if (en_cours > 0 && en_cours == record - 2) alerte_type = 'Vert';
                        if (alerte_type) {
                            activeAlerts.push({
                                type: alerte_type,
                                stat: statName,
                                record: record,
                                en_cours: en_cours
                            });
                        }
                    }
                }
                let alertsHtml = "<h3>Alertes Actives</h3>";
                if (activeAlerts.length > 0) {
                    alertsHtml += '<table class="team-alert-table"><thead><tr><th>Statistique</th><th>Série en Cours</th><th>Record</th></tr></thead><tbody>';
                    activeAlerts.forEach(alert => {
                        alertsHtml += `<tr class="${alert.type}">
                            <td>${alert.stat}</td>
                            <td>${alert.en_cours}</td>
                            <td>${alert.record}</td>
                        </tr>`;
                    });
                    alertsHtml += '</tbody></table>';
                } else {
                    alertsHtml += "<p>Aucune alerte active pour cette équipe.</p>";
                }
                alertsContainer.innerHTML = alertsHtml;
                let statsHtml = "<h3>Toutes les Caractéristiques</h3>";
                statsHtml += '<table class="team-stats-table"><tbody>';
                statsHtml += `<tr><td>Prochain Match</td><td>${stats.Prochain_Match || 'N/A'}</td></tr>`;
                statsHtml += `<tr><td>Score de Forme</td><td>${stats.Form_Score !== undefined ? stats.Form_Score.toFixed(1) : 'N/A'}</td></tr>`;
                statsHtml += `<tr><td>Détails 5 Derniers</td><td>${stats.Form_Last_5_Str || 'N/A'}</td></tr>`;
                statsHtml += `<tr><td>5 Derniers Buts (FT)</td><td>${stats.Last_5_FT_Goals || 'N/A'}</td></tr>`;
                statsHtml += `<tr><td>5 Derniers Buts (MT)</td><td>${stats.Last_5_MT_Goals || 'N/A'}</td></tr>`;
                for (const statName in STATS_CONFIG) {
                     statsHtml += `<tr>
                        <td>${statName} (Série)</td>
                        <td>${stats[statName + '_EnCours']}</td>
                     </tr>`;
                     statsHtml += `<tr>
                        <td>${statName} (Record)</td>
                        <td>${stats[statName + '_Record']}</td>
                     </tr>`;
                }
                statsHtml += '</tbody></table>';
                statsContainer.innerHTML = statsHtml;
            }
            
            function sortTable(colIndex, tableId, th) {
                const table = document.getElementById(tableId);
                if (!table) return;
                const tbody = table.querySelector("tbody");
                const rows = Array.from(tbody.querySelectorAll("tr"));
                const currentDir = th.getAttribute("data-sort-dir") || "desc";
                const newDir = currentDir === "asc" ? "desc" : "asc";
                th.setAttribute("data-sort-dir", newDir);
                table.querySelectorAll("th").forEach(header => {
                    header.classList.remove("sort-asc", "sort-desc");
                });
                th.classList.add(newDir === "asc" ? "sort-asc" : "sort-desc");
                rows.sort((a, b) => {
                    const cellA = a.querySelectorAll("td")[colIndex].innerText;
                    const cellB = b.querySelectorAll("td")[colIndex].innerText;
                    const valA = parseFloat(cellA.replace(',', '.'));
                    const valB = parseFloat(cellB.replace(',', '.'));
                    let compareA, compareB;
                    if (!isNaN(valA) && !isNaN(valB)) {
                        compareA = valA;
                        compareB = valB;
                    } else {
                        compareA = cellA.toLowerCase();
                        compareB = cellB.toLowerCase();
                    }
                    if (compareA < compareB) {
                        return newDir === "asc" ? -1 : 1;
                    }
                    if (compareA > compareB) {
                        return newDir === "asc" ? 1 : -1;
                    }
                    return 0;
                });
                rows.forEach(row => tbody.appendChild(row));
            }

            function makeTablesSortable() {
                const tables = document.querySelectorAll(".styled-table");
                tables.forEach((table, index) => {
                    const tableId = `sortable-table-${index}`;
                    table.setAttribute("id", tableId);
                    const headers = table.querySelectorAll("thead th");
                    headers.forEach((th, colIndex) => {
                        th.addEventListener("click", () => {
                            sortTable(colIndex, tableId, th);
                        });
                    });
                });
            }
            document.addEventListener("DOMContentLoaded", makeTablesSortable);
        </script>
        """

        # --- 9. Assembler le HTML Final (Inchangé) ---
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
            <header class="main-header">
                <div class="logo">ANALYSE DE MATCHS - {titre_rapport}</div>
                <nav>{nav_links}</nav>
            </header>
            
            <div class="main-content">
                <div id="welcome-message">
                    <h2>Veuillez sélectionner une catégorie dans la barre de navigation.</h2>
                </div>
                
                {team_view_html}
                
                <div class="section-container tab-content" id="form-section">
                    <h2 class="section-title">ÉTAT DE FORME ({titre_rapport})</h2>
                    {form_table_html}
                </div>
                
                <div class="section-container tab-content" id="alert-section">
                    <h2 class="section-title">TABLEAU DES ALERTES ({titre_rapport})</h2>
                    {alert_table_html}
                </div>
                
                {corps_html}
            </div>
            
            {stats_config_script}
            {json_data_script}
            
            {javascript_code}
        </body>
        </html>
        """

        with open(nom_fichier_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\nSuccès ! Le rapport V31 pour {titre_rapport} a été généré ici : {os.path.abspath(nom_fichier_html)}")

    except Exception as e:
        print(f"\nErreur lors de la génération du fichier HTML : {e}")


# --- FONCTION DE CHARGEMENT V21 (ROBUSTE + LOGIQUE DE LIGUE) ---
def charger_donnees(fichiers_csv):
    """
    Charge et combine tous les fichiers CSV.
    """
    all_dfs = []
    print(f"Chargement de {len(fichiers_csv)} fichiers...")
    
    for f in fichiers_csv:
        league_code = os.path.basename(f).replace('.csv', '')
        try:
            df_temp = pd.read_csv(f, on_bad_lines='skip')
            df_temp['LeagueCode'] = league_code 
            all_dfs.append(df_temp)
        except UnicodeDecodeError:
            print(f"  Avertissement: Échec UTF-8 pour {os.path.basename(f)}. Tentative avec 'latin1'...")
            try:
                df_temp = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
                df_temp['LeagueCode'] = league_code 
                all_dfs.append(df_temp)
            except Exception as e_latin:
                print(f"  ERREUR: Impossible de charger {os.path.basename(f)} avec UTF-8 ou latin1. Erreur : {e_latin}")
        except Exception as e:
            print(f"  ERREUR: Impossible de charger {os.path.basename(f)}. Erreur : {e}")
            
    if not all_dfs:
        print("Erreur : Aucun fichier n'a pu être chargé.")
        return None
        
    df = pd.concat(all_dfs, ignore_index=True)
    print("Données combinées avec succès.")
    
    colonnes_base = ['Date', 'HomeTeam', 'AwayTeam', 'LeagueCode']
    
    for col in colonnes_base:
        if col not in df.columns:
            print(f"ERREUR CRITIQUE: La colonne de base '{col}' est manquante. Arrêt.")
            return None
            
    if 'FTHG' not in df.columns or 'FTAG' not in df.columns:
        print("Avertissement: 'FTHG'/'FTAG' manquantes. Les stats de buts FT/Forme/CS seront ignorées.")
    if 'HTHG' not in df.columns or 'HTAG' not in df.columns:
        print("Avertissement: 'HTHG'/'HTAG' manquantes. Les stats de buts MT seront ignorées.")
    if 'FTR' not in df.columns:
        print("Avertissement: 'FTR' manquante. Les stats de Forme et Nuls seront ignorées.")

    df = df.dropna(subset=colonnes_base) 
    
    # Conversion des dates
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    if df['Date'].isna().all():
        print("Avertissement : 'dayfirst=True' a échoué, nouvelle tentative (format US)...")
        all_dfs_retry = []
        for f in fichiers_csv:
            league_code = os.path.basename(f).replace('.csv', '')
            try:
                df_temp = pd.read_csv(f, on_bad_lines='skip')
                df_temp['LeagueCode'] = league_code
                all_dfs_retry.append(df_temp)
            except UnicodeDecodeError:
                try:
                    df_temp = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
                    df_temp['LeagueCode'] = league_code
                    all_dfs_retry.append(df_temp)
                except: pass
            except: pass
        
        df = pd.concat(all_dfs_retry, ignore_index=True)
        df = df.dropna(subset=colonnes_base) 
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce') 

    df = df.dropna(subset=['Date'])
    df = df.sort_values(by='Date')
    
    # --- PRÉ-CALCUL DE TOUTES LES CONDITIONS (V21) ---
    if 'FTHG' in df.columns and 'FTAG' in df.columns:
        df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce')
        df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce')
        df = df.dropna(subset=['FTHG', 'FTAG'])
        
        df['TotalGoals'] = df['FTHG'] + df['FTAG']
        df['Cond_Moins_0_5_FT'] = df['TotalGoals'] < 0.5   # 0
        df['Cond_Plus_1_5_FT']  = df['TotalGoals'] > 1.5   # 2+
        df['Cond_Moins_1_5_FT'] = df['TotalGoals'] < 1.5   # 0-1
        df['Cond_Plus_2_5_FT']  = df['TotalGoals'] > 2.5   # 3+
        df['Cond_Moins_2_5_FT'] = df['TotalGoals'] < 2.5   # 0-2
        df['Cond_Plus_3_5_FT']  = df['TotalGoals'] > 3.5   # 4+
        df['Cond_Moins_3_5_FT'] = df['TotalGoals'] < 3.5   # 0-3
    
    if 'HTHG' in df.columns and 'HTAG' in df.columns:
        df['HTHG'] = pd.to_numeric(df['HTHG'], errors='coerce')
        df['HTAG'] = pd.to_numeric(df['HTAG'], errors='coerce')
        df = df.dropna(subset=['HTHG', 'HTAG'])
        
        df['TotalHTGoals'] = df['HTHG'] + df['HTAG']
        df['Cond_Plus_0_5_HT']  = df['TotalHTGoals'] > 0.5 # 1+ MT
        df['Cond_Moins_0_5_HT'] = df['TotalHTGoals'] < 0.5 # 0 MT
        df['Cond_Plus_1_5_HT']  = df['TotalHTGoals'] > 1.5 # 2+ MT
        df['Cond_Moins_1_5_HT'] = df['TotalHTGoals'] < 1.5 # 0-1 MT
        
    if 'FTR' in df.columns:
        df = df.dropna(subset=['FTR'])
        df['Cond_Draw_FT'] = df['FTR'] == 'D' 
    
    print("Toutes les données ont été préparées et les conditions pré-calculées.")
    return df

# --- (NOUVEAU V31.1) Fonction Helper ---
def trouver_max_serie_pour_colonne(df_equipe, nom_colonne_condition):
    """
    Helper: Calcule la série max pour une colonne de condition.
    """
    if nom_colonne_condition not in df_equipe.columns:
        return 0 
        
    df_equipe = df_equipe.sort_values(by='Date')
    df_equipe['streak_group'] = (df_equipe[nom_colonne_condition] != df_equipe[nom_colonne_condition].shift()).cumsum()
    streaks_when_true = df_equipe[df_equipe[nom_colonne_condition] == True]

    if streaks_when_true.empty:
        max_streak = 0
    else:
        streak_lengths = streaks_when_true.groupby('streak_group').size()
        max_streak = int(streak_lengths.max())
    return max_streak

# --- (NOUVEAU V31.1) Fonction Helper ---
def trouver_serie_en_cours_pour_colonne(df_equipe, nom_colonne_condition):
    """
    Helper: Calcule la série en cours (en comptant à rebours) 
    pour une colonne de condition.
    """
    if nom_colonne_condition not in df_equipe.columns:
        return 0 
        
    df_equipe = df_equipe.sort_values(by='Date')
    conditions_list = df_equipe[nom_colonne_condition].tolist()
    
    serie_en_cours = 0
    for condition_remplie in reversed(conditions_list):
        if condition_remplie:
            serie_en_cours += 1
        else:
            break
    return serie_en_cours


# --- FONCTION HELPER (V29 - Forme simplifiée) ---
def calculer_score_de_forme(df_equipe, equipe):
    """
    Calcule le score de forme pondéré sur les 5 derniers matchs.
    MODIFIÉ V29: Renvoie 'V, D, N' au lieu de 'V (2-1)'
    """
    if 'FTR' not in df_equipe.columns or 'FTHG' not in df_equipe.columns:
        return 0, "N/A" # Impossible de calculer
    df_equipe = df_equipe.sort_values(by='Date')
    last_5_games = df_equipe.tail(5)
    if len(last_5_games) < 5:
        return 0, "Pas assez de matchs"
    scores = []
    details_str = []
    ponderations = [0.2, 0.4, 0.6, 0.8, 1.0] # [plus ancien, ..., plus récent]
    idx = 0
    for i, (index, match) in enumerate(last_5_games.iterrows()):
        score_match = 0
        resultat = match['FTR']
        if (match['HomeTeam'] == equipe and resultat == 'H') or (match['AwayTeam'] == equipe and resultat == 'A'):
            score_match += 5 # Victoire
            resultat_str = "V"
        elif resultat == 'D':
            score_match += 1 # Nul
            resultat_str = "N"
        else:
            score_match -= 3 # Défaite
            resultat_str = "D"
        buts_marques = 0
        buts_encaisses = 0
        if match['HomeTeam'] == equipe:
            buts_marques = match['FTHG']
            buts_encaisses = match['FTAG']
        else:
            buts_marques = match['FTAG']
            buts_encaisses = match['FTHG']
        if buts_marques >= 3: score_match += 2 # Bonus Offensif
        if buts_encaisses == 0: score_match += 2 # Bonus Défensif (Clean Sheet)
        score_pondere = score_match * ponderations[idx]
        scores.append(score_pondere)
        idx += 1
        details_str.append(resultat_str) # --- LIGNE MODIFIÉE V29 ---
    total_score = sum(scores)
    details_complets = ", ".join(reversed(details_str))
    return total_score, details_complets


# --- (MODIFIÉ V31) FONCTION DE CALCUL V31 ---
def calculer_tous_les_records_et_series(df, equipes, odds_api_dict):
    """
    Calcule le RECORD, la SÉRIE EN COURS, les 5 DERNIERS BUTS,
    le SCORE DE FORME, et le PROCHAIN MATCH.
    
    MODIFIÉ V31: Utilise 'odds_api_dict' comme SEULE source 
                 pour le "Prochain Match".
    """
    resultats = []
    conditions_a_tester = {
        'FT Marque': 'Cond_FT_Score', 'FT CS': 'Cond_FT_CS', 'FT No CS': 'Cond_FT_No_CS',
        'FT -0.5': 'Cond_Moins_0_5_FT', 'FT +1.5': 'Cond_Plus_1_5_FT',
        'FT -1.5': 'Cond_Moins_1_5_FT', 'FT +2.5': 'Cond_Plus_2_5_FT',
        'FT -2.5': 'Cond_Moins_2_5_FT', 'FT +3.5': 'Cond_Plus_3_5_FT',
        'FT -3.5': 'Cond_Moins_3_5_FT', 'FT Nuls': 'Cond_Draw_FT', 
        'MT +0.5': 'Cond_Plus_0_5_HT', 'MT -0.5': 'Cond_Moins_0_5_HT',
        'MT +1.5': 'Cond_Plus_1_5_HT', 'MT -1.5': 'Cond_Moins_1_5_HT',
    }
    print("Calcul des records, séries, 5 derniers buts et score de forme...")
    for equipe in equipes:
        df_equipe = df[
            (df['HomeTeam'] == equipe) | (df['AwayTeam'] == equipe)
        ].copy()
        if df_equipe.empty: continue
        record_equipe = {'Équipe': equipe}
        df_equipe = df_equipe.sort_values(by='Date')
        
        if 'TotalGoals' in df_equipe.columns:
            last_5_ft_goals = df_equipe['TotalGoals'].tail(5).astype(int).tolist()
            record_equipe['Last_5_FT_Goals'] = ", ".join(map(str, last_5_ft_goals))
        else: record_equipe['Last_5_FT_Goals'] = "N/A"
        if 'TotalHTGoals' in df_equipe.columns:
            last_5_mt_goals = df_equipe['TotalHTGoals'].tail(5).astype(int).tolist()
            record_equipe['Last_5_MT_Goals'] = ", ".join(map(str, last_5_mt_goals))
        else: record_equipe['Last_5_MT_Goals'] = "N/A"
            
        score_forme, details_forme = calculer_score_de_forme(df_equipe, equipe)
        record_equipe['Form_Score'] = score_forme
        record_equipe['Form_Last_5_Str'] = details_forme
        
        if 'FTHG' in df_equipe.columns:
            df_equipe['ButsMarques'] = np.where(df_equipe['HomeTeam'] == equipe, df_equipe['FTHG'], df_equipe['FTAG'])
            df_equipe['ButsEncaisses'] = np.where(df_equipe['HomeTeam'] == equipe, df_equipe['FTAG'], df_equipe['FTHG'])
            df_equipe['Cond_FT_Score'] = df_equipe['ButsMarques'] > 0
            df_equipe['Cond_FT_CS'] = df_equipe['ButsEncaisses'] == 0
            df_equipe['Cond_FT_No_CS'] = df_equipe['ButsEncaisses'] > 0
            
        # --- (MODIFIÉ V31) Récupérer le prochain match (API Cotes uniquement) ---
        prochain = "N/A"
        match_info = odds_api_dict.get(equipe) # 1. Match exact
        if not match_info: # 2. Match flou (CSV in API)
            for api_nom, api_match_data in odds_api_dict.items():
                if equipe in api_nom:
                    match_info = api_match_data
                    break
        if not match_info: # 3. Match flou (API in CSV)
            for api_nom, api_match_data in odds_api_dict.items():
                if api_nom in equipe:
                    match_info = api_match_data
                    break
        
        if match_info:
            opponent = match_info.get('opponent', '?')
            loc = match_info.get('loc', '?')
            loc_str = "Dom" if loc == "Home" else "Ext"
            
            # Formater la date
            start_time_iso = match_info.get('commence_time')
            try:
                # Convertir la date ISO UTC en objet datetime
                utc_date = pd.to_datetime(start_time_iso)
                # Formater en dd/mm HH:MM
                date_str = utc_date.strftime('%d/%m %H:%M')
            except:
                date_str = "Date?" # Fallback
                
            prochain = f"{date_str} -> {opponent} ({loc_str})"
        
        record_equipe['Prochain_Match'] = prochain
        # --- FIN MODIFICATION V31 ---
            
        for nom_base, nom_col_data in conditions_a_tester.items():
            record = trouver_max_serie_pour_colonne(df_equipe, nom_col_data)
            record_equipe[f'{nom_base}_Record'] = record
            en_cours = trouver_serie_en_cours_pour_colonne(df_equipe, nom_col_data)
            record_equipe[f'{nom_base}_EnCours'] = en_cours
            
        resultats.append(record_equipe)
    df_rapport_final = pd.DataFrame(resultats)
    df_rapport_final = df_rapport_final.sort_values(by='Équipe').reset_index(drop=True)
    return df_rapport_final


# --- FONCTION DE DÉCOUVERTE V17 ---
def decouvrir_ligues_et_equipes(dossier_csv_principal):
    ligues_a_analyser = {}
    try:
        dossiers_saison = sorted([
            f for f in glob.glob(f"{dossier_csv_principal}/*") if os.path.isdir(f) and os.path.basename(f).startswith('data')
        ])
        if not dossiers_saison:
            print(f"Erreur : Aucun dossier de saison (ex: 'data2010-2011') trouvé dans '{dossier_csv_principal}'")
            return {}
        dossier_le_plus_recent = dossiers_saison[-1]
        print(f"Dossier de la saison la plus récente détecté : {os.path.basename(dossier_le_plus_recent)}")
    except Exception as e:
        print(f"Erreur lors de la recherche des dossiers de saison : {e}")
        return {}
    fichiers_ligue = glob.glob(f"{dossier_le_plus_recent}/*.csv")
    if not fichiers_ligue:
        print(f"Erreur : Aucun fichier CSV de ligue trouvé dans '{dossier_le_plus_recent}'")
        return {}
    print(f"\n--- {len(fichiers_ligue)} LIGUES DÉTECTÉES ---")
    for fichier_path in fichiers_ligue:
        code_ligue = os.path.basename(fichier_path).replace('.csv', '')
        try:
            try: df_actuel = pd.read_csv(fichier_path)
            except UnicodeDecodeError: df_actuel = pd.read_csv(fichier_path, encoding='latin1')
            equipes_domicile = df_actuel['HomeTeam'].dropna().unique()
            equipes_exterieur = df_actuel['AwayTeam'].dropna().unique()
            equipes_actuelles = sorted(list(set(equipes_domicile) | set(equipes_exterieur)))
            if equipes_actuelles:
                ligues_a_analyser[code_ligue] = equipes_actuelles
                nom_lisible = LEAGUE_NAME_MAPPING.get(code_ligue, f"Code Inconnu: {code_ligue}")
                print(f"  - {code_ligue} -> {nom_lisible} ({len(equipes_actuelles)} équipes trouvées)")
            else:
                print(f"  - Avertissement: {code_ligue} est vide ou ne contient pas d'équipes.")
        except Exception as e:
            print(f"  Erreur lors de la lecture du fichier {code_ligue}.csv : {e}")
    return ligues_a_analyser


# --- (SUPPRIMÉ V31) Ancienne fonction charger_prochains_matchs_api ---


# --- (NOUVEAU V30 / MODIFIÉ V31) FONCTION API POUR LES COTES ---
def charger_cotes_via_api(api_key, codes_ligues_utilisateur):
    """
    Charge les cotes ET les infos de match depuis 'The Odds API'.
    C'est maintenant la SEULE source de données futures.
    """
    if not api_key or "VOTRE_CLÉ" in api_key:
        print("\n" + "="*50)
        print("  ERREUR : Clé API non configurée dans config.py")
        print("  Impossible de charger les cotes ou les prochains matchs.")
        print("="*50 + "\n")
        return {}
        
    print(f"\nChargement des Cotes & Matchs via 'The Odds API' pour {len(codes_ligues_utilisateur)} ligues...")
    
    # 1. Construire la liste des ligues à interroger
    regions = 'eu' # Europe
    markets = 'h2h,totals,btts' # 1X2, Over/Under, Both Teams To Score
    
    ligues_api_string = []
    for code in codes_ligues_utilisateur:
        api_league_name = ODDS_API_LEAGUE_MAP.get(code)
        if api_league_name:
            ligues_api_string.append(api_league_name)
        else:
            print(f"  - Avertissement: Pas de mapping 'The Odds API' pour '{code}'. Cotes ignorées.")
    
    if not ligues_api_string:
        print("  - ERREUR: Aucune ligue à interroger pour les cotes.")
        return {}

    # 2. Faire l'appel API (un seul appel pour toutes les ligues)
    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/"
        params = {
            'apiKey': api_key,
            'regions': regions,
            'markets': markets,
            'sports': ','.join(ligues_api_string),
            'oddsFormat': 'decimal',
            'bookmakers': 'bet365' # On demande bet365, mais on prendra ce qu'on trouve
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"  - Cotes reçues. Utilisation restante: {response.headers.get('x-requests-remaining')}")
        
    except requests.exceptions.HTTPError as e_http:
        print(f"  - ERREUR HTTP {e_http.response.status_code} en appelant 'The Odds API'.")
        print(f"  - Réponse: {e_http.response.text}")
        return {}
    except requests.exceptions.RequestException as e:
        print(f"  - ERREUR Réseau en appelant 'The Odds API': {e}")
        return {}
    except Exception as e_general:
        print(f"  - ERREUR Inconnue lors du chargement des cotes: {e_general}")
        return {}

    # 3. Parser la réponse et la transformer en dictionnaire
    final_odds_dict = {}
    for match in data:
        home_team = match.get('home_team')
        away_team = match.get('away_team')
        start_time = match.get('commence_time') # NOUVEAU V31
        if not home_team or not away_team: continue
        
        odds_data = {}
        
        # Trouver un bookmaker (bet365 en priorité, sinon le premier)
        if not match.get('bookmakers'):
            print(f"  - Avertissement: Pas de bookmakers trouvés pour {home_team} vs {away_team}")
            continue
            
        bookie = next((b for b in match['bookmakers'] if b['key'] == 'bet365'), match['bookmakers'][0])
        
        for market in bookie['markets']:
            try:
                # --- PARSER LE MARCHÉ H2H (1X2) ---
                if market['key'] == 'h2h':
                    outcomes = market['outcomes']
                    if len(outcomes) == 3:
                        if outcomes[0]['name'] == home_team:
                            odds_data['API_H'] = outcomes[0]['price']
                            odds_data['API_A'] = outcomes[2]['price']
                        else: 
                            odds_data['API_H'] = outcomes[2]['price']
                            odds_data['API_A'] = outcomes[0]['price']
                        odds_data['API_D'] = outcomes[1]['price']
                        if 'API_H' in odds_data and 'API_A' in odds_data:
                            prob_H = 1 / odds_data['API_H']
                            prob_A = 1 / odds_data['API_A']
                            odds_data['API_12'] = 1 / (prob_H + prob_A)

                # --- PARSER LE MARCHÉ TOTALS (Over/Under) ---
                elif market['key'] == 'totals':
                    for outcome in market['outcomes']:
                        point = outcome.get('point')
                        name = outcome.get('name')
                        price = outcome.get('price')
                        if point == 0.5 and name == 'Over': odds_data['API_Over_0_5'] = price
                        if point == 0.5 and name == 'Under': odds_data['API_Under_0_5'] = price
                        if point == 1.5 and name == 'Over': odds_data['API_Over_1_5'] = price
                        if point == 1.5 and name == 'Under': odds_data['API_Under_1_5'] = price
                        if point == 2.5 and name == 'Over': odds_data['API_Over_2_5'] = price
                        if point == 2.5 and name == 'Under': odds_data['API_Under_2_5'] = price
                        if point == 3.5 and name == 'Over': odds_data['API_Over_3_5'] = price
                        if point == 3.5 and name == 'Under': odds_data['API_Under_3_5'] = price

                # --- PARSER LE MARCHÉ BTTS (Both Teams To Score) ---
                elif market['key'] == 'btts':
                    for outcome in market['outcomes']:
                        name = outcome.get('name')
                        price = outcome.get('price')
                        if name == 'Yes': odds_data['API_BTTS_Yes'] = price
                        if name == 'No': odds_data['API_BTTS_No'] = price
            
            except Exception as e_market:
                print(f"    - Avertissement: Erreur parsing marché {market.get('key')} pour {home_team}: {e_market}")

        # Stocker pour les deux équipes, en utilisant le nom de l'API
        # On ajoute 'commence_time' (V31)
        if odds_data:
            match_data = {
                'opponent': away_team, 'loc': 'Home', 
                'odds': odds_data, 'commence_time': start_time
            }
            final_odds_dict[home_team] = match_data
            
            match_data_away = {
                'opponent': home_team, 'loc': 'Away', 
                'odds': odds_data, 'commence_time': start_time
            }
            final_odds_dict[away_team] = match_data_away

    print(f"Succès : {len(final_odds_dict)} équipes avec cotes/matchs chargées depuis 'The Odds API'.")
    return final_odds_dict


# --- FONCTION HUB V15 ---
def creer_page_hub(rapports):
    nom_fichier = "index.html"
    titre_page = "Hub d'Analyse des Ligues"
    rapports = sorted(rapports, key=lambda x: x['nom_ligue'])
    links_html = ""
    for rapport in rapports:
        links_html += f'<li><a href="{rapport["nom_fichier"]}">{rapport["nom_ligue"]}</a></li>\n'
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{titre_page}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f0f2f5; margin: 0; padding: 0;
                display: flex; justify-content: center; align-items: center; min-height: 100vh;
            }}
            .container {{
                background-color: #ffffff; padding: 40px; border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); text-align: center;
                max-width: 600px; width: 90%;
            }}
            h1 {{ color: #222; margin-top: 0; }}
            p {{ color: #555; font-size: 1.1em; }}
            ul {{ list-style-type: none; padding: 0; margin-top: 30px; }}
            li {{ margin-bottom: 15px; }}
            a {{
                display: block; background-color: #007bff; color: white;
                text-decoration: none; padding: 15px 20px; border-radius: 5px;
                font-weight: bold; font-size: 1.1em;
                transition: background-color 0.3s, transform 0.2s;
            }}
            a:hover {{ background-color: #0056b3; transform: translateY(-2px); }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{titre_page}</h1>
            <p>Veuillez sélectionner une ligue à analyser :</p>
            <ul>{links_html}</ul>
        </div>
    </body>
    </html>
    """
    try:
        with open(nom_fichier, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\nSuccès ! La page d'accueil '{nom_fichier}' a été créée.")
    except Exception as e:
        print(f"\nErreur lors de la création de la page d'accueil '{nom_fichier}': {e}")


# --- POINT D'ENTRÉE DU SCRIPT (MODIFIÉ V31) ---
if __name__ == "__main__":
    
    # !! IMPORTANT !! 
    SAISON_API = 2025 # (Inutilisé par The Odds API, mais gardé au cas où)
    
    dossier_csv_principal = "CSV_Data" 
    
    # 1. Trouver TOUS les fichiers CSV (sauf fixtures.csv)
    tous_les_fichiers_csv = []
    for f in glob.glob(f"{dossier_csv_principal}/**/*.csv", recursive=True):
        if os.path.basename(f).lower() != "fixtures.csv":
            tous_les_fichiers_csv.append(f)
    tous_les_fichiers_csv = sorted(tous_les_fichiers_csv)
    
    if not tous_les_fichiers_csv:
        print(f"Erreur : Aucun fichier .csv n'a été trouvé dans les sous-dossiers de '{dossier_csv_principal}'")
        exit()
            
    # 2. Identifier les ligues et les équipes de la saison la plus récente
    ligues_a_analyser = decouvrir_ligues_et_equipes(dossier_csv_principal)
    if not ligues_a_analyser:
        print("Erreur : Aucune ligue ou équipe n'a pu être identifiée.")
        exit()
    
    # 3. Étape 1 : Chargement (tous les fichiers en une fois)
    donnees_completes = charger_donnees(tous_les_fichiers_csv)
    
    # 4. (MODIFIÉ V31) Charger les COTES & MATCHS via 'The Odds API'
    if not hasattr(config, 'API_KEY'):
        print("\nERREUR: 'API_KEY' non trouvée dans config.py. Arrêt.")
        print("Veuillez mettre votre clé 'The Odds API' dans config.py.")
        exit()
        
    odds_api_dict = charger_cotes_via_api(
        config.API_KEY, 
        ligues_a_analyser.keys()
    )
    
    # 5. (SUPPRIMÉ V31) L'appel à 'api-football.com' a été retiré.
    
    rapports_generes_pour_hub = []
    
    if donnees_completes is not None:
        
        # 6. Boucle pour traiter CHAQUE ligue
        for code_ligue, equipes_a_analyser in ligues_a_analyser.items():
            
            nom_ligue_lisible = LEAGUE_NAME_MAPPING.get(code_ligue, code_ligue)
            print(f"\n--- DÉBUT DU TRAITEMENT : {nom_ligue_lisible} ({code_ligue}) ---")
            print(f"Analyse de {len(equipes_a_analyser)} équipes...")

            # 7. Étape 3 : Calculer tous les records ET séries en cours
            # (MODIFIÉ V31)
            df_rapport_ligue = calculer_tous_les_records_et_series(
                donnees_completes, 
                equipes_a_analyser, 
                odds_api_dict           # Dico API Cotes (seule source)
            )

            # 8. Étape 4 (Affichage console)
            print(f"\n--- RÉSULTAT ({nom_ligue_lisible}) ---")
            pd.set_option('display.max_rows', 5) # Afficher un aperçu
            print(df_rapport_ligue)
            pd.reset_option('display.max_rows')
            
            # 9. ÉTAPE 5 : SAUVEGARDE EN HTML
            nom_fichier_propre = nom_ligue_lisible.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '')
            nom_du_fichier_html = f"rapport_{nom_fichier_propre}.html"
            titre_rapport = f"{nom_ligue_lisible}"
            
            sauvegarder_en_html_v22(
                df_rapport_ligue, 
                nom_du_fichier_html, 
                titre_rapport,
                odds_api_dict # On passe le dictionnaire de cotes de l'API
            )
            
            rapports_generes_pour_hub.append({
                'nom_ligue': nom_ligue_lisible,
                'nom_fichier': nom_du_fichier_html
            })
        
        # 10. Créer la page d'accueil (index.html)
        creer_page_hub(rapports_generes_pour_hub)
        
        print("\n--- TRAITEMENT TERMINÉ ---")
        print(f"La page d'accueil 'index.html' a été créée avec les liens vers {len(rapports_generes_pour_hub)} rapports.")
        
    else:
        print("Erreur : Le chargement des données a échoué. Le script s'arrête.")