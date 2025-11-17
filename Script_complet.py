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
# --- Dictionnaire de Mapping (THE ODDS API) ---
# ##########################################################################
ODDS_API_LEAGUE_MAP = {
    'E0': 'soccer_epl', 'E1': 'soccer_england_championship',
    'D1': 'soccer_germany_bundesliga', 'D2': 'soccer_germany_bundesliga_2',
    'F1': 'soccer_france_ligue_1', 'F2': 'soccer_france_ligue_2',
    'I1': 'soccer_italy_serie_a', 'I2': 'soccer_italy_serie_b',
    'SP1': 'soccer_spain_la_liga', 'SP2': 'soccer_spain_la_liga_2',
    'N1': 'soccer_netherlands_eredivisie', 'P1': 'soccer_portugal_primeira_liga',
    'SC0': 'soccer_scotland_premiership', 'B1': 'soccer_belgium_first_div',
    'T1': 'soccer_turkey_super_league', 'G1': 'soccer_greece_super_league_1',
}

# ##########################################################################
# --- Dictionnaire de Mapping Cotes/Alertes ---
# ##########################################################################
STAT_TO_ODD_COLUMN_MAP = {
    'FT +1.5': 'API_Under_1_5', 'FT +2.5': 'API_Under_2_5', 'FT +3.5': 'API_Under_3_5',
    'FT -0.5': 'API_Over_0_5', 'FT -1.5': 'API_Over_1_5', 'FT -2.5': 'API_Over_2_5',
    'FT -3.5': 'API_Over_3_5', 
    'FT CS': 'API_BTTS_Yes', 'FT No CS': 'API_BTTS_No', 'FT Nuls': 'API_12',
    'MT +0.5': 'API_MT_Under_0_5', 'MT -0.5': 'API_MT_Over_0_5',
    'MT +1.5': 'API_MT_Under_1_5', 'MT -1.5': 'API_MT_Over_1_5',
    'FT Marque': 'API_Team_Under_0_5',
}
# ##########################################################################

# (V33) Définir les noms de colonnes pour les stats
STATS_COLUMNS_BASE = [
    'FT Marque', 'FT CS', 'FT No CS',
    'FT -0.5', 'FT +1.5', 'FT -1.5', 'FT +2.5', 'FT -2.5', 'FT +3.5', 'FT -3.5', 
    'FT Nuls', 
    'MT +0.5', 'MT -0.5', 'MT +1.5', 'MT -1.5'
]

# --- (MODIFIÉ V39) Helper 1: Style pour les tableaux (6 colonnes) ---
def colorier_series_v19(row):
    """
    Applique un style aux 6 colonnes (Ligue, Équipe, Record, Année Record, Série, 5 Derniers).
    """
    record = row['Record']
    en_cours = row['Série en Cours']
    
    style_ligue = 'font-weight: normal; color: #777; font-size: 0.9em; text-align: left;'
    style_equipe = '' 
    style_record = '' 
    style_annee_record = 'font-weight: normal; color: #777; font-size: 0.9em; text-align: center;'
    style_en_cours = 'font-weight: normal; color: #555;' 
    style_5_derniers = 'font-weight: normal; color: #777; font-size: 0.9em;' 

    if en_cours > 0 and en_cours == record:
        style_en_cours = 'background-color: #ffebee; color: #c62828; font-weight: bold;'
    elif en_cours > 0 and en_cours == record - 1:
        style_en_cours = 'background-color: #fff3e0; color: #f57c00; font-weight: bold;'
    elif en_cours > 0 and en_cours == record - 2:
        style_en_cours = 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    
    return [style_ligue, style_equipe, style_record, style_annee_record, style_en_cours, style_5_derniers] 

# --- (MODIFIÉ V39) Helper 2: Style pour le tableau d'alertes (10 colonnes) ---
def colorier_tableau_alertes_v22(row):
    """
    Applique un style à la ligne du tableau d'alertes (V39).
    Gère 10 colonnes (avec 'Ligue' et 'Année Record')
    """
    alerte_type = row['Alerte']
    style_base = ''
    if alerte_type == 'Rouge':
        style_base = 'background-color: #ffebee; color: #c62828; font-weight: bold;'
    elif alerte_type == 'Orange':
        style_base = 'background-color: #fff3e0; color: #f57c00; font-weight: bold;'
    elif alerte_type == 'Vert':
        style_base = 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    
    style_ligue = style_base + 'font-weight: normal; color: #333; font-size: 0.9em; text-align: left;'
    style_annee_record = style_base + 'font-weight: normal; color: #333; font-size: 0.9em; text-align: center;' # NOUVEAU V39
    style_5_derniers = style_base + 'font-weight: normal; color: #333; font-size: 0.9em;'
    style_prochain_match = style_base + 'font-weight: normal; color: #17a2b8; font-size: 0.9em;'
    
    # Ordre: Ligue, Équipe, Stat, Record, Année Record, Série, 5 Derniers, Prochain Match, Cote, Alerte(cachée)
    return [
        style_ligue, style_base, style_base, style_base, style_annee_record, style_base, 
        style_5_derniers, style_prochain_match, style_base, style_base
    ]

# --- (MODIFIÉ V32) Helper 3: Style pour le tableau de Forme (5 colonnes) ---
def colorier_forme_v22(row):
    """
    Colore le Score de Forme. Gère 5 colonnes (avec 'Ligue').
    """
    score = row['Score de Forme']
    
    style_ligue = 'font-weight: normal; color: #777; font-size: 0.9em; text-align: left;'
    style_equipe = ''
    style_score = ''
    style_details = 'font-weight: normal; color: #777; font-size: 0.9em;'
    style_prochain_match = 'font-weight: normal; color: #17a2b8; font-size: 0.9em;'
    
    if score > 10: style_score = 'color: #2e7d32; font-weight: bold;'
    elif score > 0: style_score = 'color: #28a745;'
    elif score < -5: style_score = 'color: #c62828; font-weight: bold;'
    elif score < 0: style_score = 'color: #dc3545;'
    
    return [style_ligue, style_equipe, style_score, style_details, style_prochain_match]


# --- (NOUVEAU V37) Helper 5: Formater les pilules de forme ---
def formater_forme_html(forme_string):
    """
    Convertit "V, D, N" en pilules HTML colorées.
    """
    if forme_string == "N/A" or not forme_string:
        return "N/A"
        
    mapping = {
        'V': '<span class="form-pill form-v">V</span>',
        'N': '<span class="form-pill form-n">N</span>',
        'D': '<span class="form-pill form-d">D</span>',
    }
    
    pills = [mapping.get(resultat.strip(), resultat) for resultat in forme_string.split(',')]
    return " ".join(pills)


# --- (MODIFIÉ V39.1) Helper 6: Génération de la page HTML ---
def sauvegarder_rapport_global_html(
    df_rapport_complet, 
    df_series_brisees, 
    count_brisees,      
    count_actives,      
    df_last_week,  
    nom_fichier_html, 
    titre_rapport, 
    odds_api_dict
):
    """
    Sauvegarde le DataFrame GLOBAL en un seul fichier index.html.
    MODIFIÉ V39.1: Corrige un bug de formatage str/float sur 'Année Record'.
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
        nav_links += '<a href="#" onclick="showSection(\'dashboard-section\', this); event.preventDefault();" class="dashboard-button active">📊 Tableau de Bord</a>\n'
        nav_links += '<a href="#" onclick="showSection(\'last-week-section\', this); event.preventDefault();" class="history-button">📅 Résultats Semaine</a>\n'
        nav_links += '<a href="#" onclick="showSection(\'broken-series-section\', this); event.preventDefault();" class="broken-button">💥 Séries Brisées</a>\n'
        nav_links += '<a href="#" onclick="showSection(\'team-view-section\', this); event.preventDefault();" class="team-button">🔍 Par Équipe</a>\n'
        nav_links += '<a href="#" onclick="showSection(\'alert-section\', this); event.preventDefault();" class="alert-button">⚠️ Alertes (Rouges)</a>\n'
        nav_links += '<a href="#" onclick="showSection(\'pre-alert-section\', this); event.preventDefault();" class="pre-alert-button">🟠 Pré-Alertes (O/V)</a>\n'
        for nom_base, config in stats_a_afficher.items():
            id_html = config[0]
            nav_links += f'<a href="#" onclick="showSection(\'{id_html}\', this); event.preventDefault();">{nom_base}</a>\n'
        
        # --- NOUVEAU V37: Obtenir la liste des ligues pour le filtre ---
        liste_ligues = sorted(df_rapport_complet['Ligue'].unique())
        filtre_ligue_html = '<select id="league-filter" onchange="filterTablesByLeague(this.value);"><option value="Toutes">Toutes les Ligues</option>'
        for ligue in liste_ligues:
            filtre_ligue_html += f'<option value="{ligue}">{ligue}</option>'
        filtre_ligue_html += '</select>'

        # --- 3. Générer les tableaux d'alertes (MODIFIÉ V39) ---
        alertes_collectees_rouges = []
        alertes_collectees_pre = [] 
        count_pre_alertes = 0

        for nom_base, config in stats_a_afficher.items():
            col_record = f'{nom_base}_Record'
            col_annee = f'{nom_base}_Annee_Record' 
            col_en_cours = f'{nom_base}_EnCours'
            col_5_derniers = 'Last_5_FT_Goals' if nom_base.startswith('FT') else 'Last_5_MT_Goals'
            
            for index, row in df_rapport_complet.iterrows():
                equipe = row['Équipe'] 
                ligue = row['Ligue']
                if col_record not in row or pd.isna(row[col_record]): continue
                record = row[col_record]
                annee_record = row[col_annee] 
                en_cours = row[col_en_cours]
                cinq_derniers_str = row.get(col_5_derniers, "N/A")
                prochain_match_str = row.get('Prochain_Match', "N/A")
                
                alerte_type = None
                if en_cours > 0 and en_cours == record: alerte_type = 'Rouge'
                elif en_cours > 0 and en_cours == record - 1: alerte_type = 'Orange'
                elif en_cours > 0 and en_cours == record - 2: alerte_type = 'Vert'
                
                if alerte_type:
                    cote_pari = "N/A"
                    nom_col_cote = STAT_TO_ODD_COLUMN_MAP.get(nom_base)
                    
                    if nom_col_cote:
                        match_info = odds_api_dict.get(equipe)
                        if not match_info:
                            for api_nom, api_match_data in odds_api_dict.items():
                                if equipe in api_nom: match_info = api_match_data; break
                        if not match_info:
                            for api_nom, api_match_data in odds_api_dict.items():
                                if api_nom in equipe: match_info = api_match_data; break
                        if match_info:
                            cote = match_info['odds'].get(nom_col_cote)
                            if cote: cote_pari = f"{cote:.2f}"
                            else: cote_pari = f"({nom_col_cote.split('_')[-1]}?)"
                        else: cote_pari = "(Match?)"
                    else: cote_pari = "(Stat?)"
                    
                    data_dict = {
                        'Ligue': ligue,
                        'Équipe': equipe, 'Statistique': nom_base, 'Record': record,
                        'Année Record': annee_record, 
                        'Série en Cours': en_cours, '5 Derniers Buts': cinq_derniers_str, 
                        'Prochain Match': prochain_match_str, 'Cote (Pari Inverse)': cote_pari,
                        'Alerte': alerte_type 
                    }
                    
                    if alerte_type == 'Rouge':
                        alertes_collectees_rouges.append(data_dict)
                    else:
                        alertes_collectees_pre.append(data_dict)

        # 3.1 Tableau Alertes ROUGES
        if not alertes_collectees_rouges:
            alert_table_html = "<h3 class='no-alerts'>Aucune alerte Rouge active pour le moment.</h3>"
        else:
            df_alertes = pd.DataFrame(alertes_collectees_rouges)
            df_alertes['Alerte'] = pd.Categorical(df_alertes['Alerte'], categories=["Rouge"], ordered=True)
            df_alertes = df_alertes.sort_values(by=['Ligue', 'Équipe']).reset_index(drop=True)
            colonnes_ordre = [
                'Ligue', 'Équipe', 'Statistique', 'Record', 'Année Record', # V39
                'Série en Cours', '5 Derniers Buts', 'Prochain Match', 'Cote (Pari Inverse)', 'Alerte'
            ]
            df_alertes = df_alertes.reindex(columns=colonnes_ordre)
            # CORRIGÉ V39.1: 'Année Record' formaté en '{}' (texte)
            styler_alertes = df_alertes.style.apply(colorier_tableau_alertes_v22, axis=1) \
                                        .set_table_attributes('class="styled-table alerts-table filterable-table"') \
                                        .format({'Cote (Pari Inverse)': '{}', 'Année Record': '{}'}) \
                                        .hide(axis="index") \
                                        .hide(['Alerte'], axis=1) 
            alert_table_html = styler_alertes.to_html()

        # 3.2 NOUVEAU Tableau Pré-Alertes (ORANGE / VERT)
        if not alertes_collectees_pre:
            pre_alert_table_html = "<h3 class='no-alerts'>Aucune pré-alerte (Orange ou Vert) active.</h3>"
        else:
            df_alertes_pre = pd.DataFrame(alertes_collectees_pre)
            df_alertes_pre['Alerte'] = pd.Categorical(df_alertes_pre['Alerte'], categories=["Orange", "Vert"], ordered=True)
            df_alertes_pre = df_alertes_pre.sort_values(by=['Alerte', 'Ligue', 'Équipe']).reset_index(drop=True)
            colonnes_ordre = [
                'Ligue', 'Équipe', 'Statistique', 'Record', 'Année Record', # V39
                'Série en Cours', '5 Derniers Buts', 'Prochain Match', 'Cote (Pari Inverse)', 'Alerte'
            ]
            df_alertes_pre = df_alertes_pre.reindex(columns=colonnes_ordre)
            # CORRIGÉ V39.1: 'Année Record' formaté en '{}' (texte)
            styler_pre_alertes = df_alertes_pre.style.apply(colorier_tableau_alertes_v22, axis=1) \
                                        .set_table_attributes('class="styled-table alerts-table filterable-table"') \
                                        .format({'Cote (Pari Inverse)': '{}', 'Année Record': '{}'}) \
                                        .hide(axis="index") \
                                        .hide(['Alerte'], axis=1) 
            pre_alert_table_html = styler_pre_alertes.to_html()
            
        count_alertes_rouges = len(alertes_collectees_rouges)
        count_pre_alertes = len(alertes_collectees_pre)

        # --- 4. Générer le tableau de Forme (POUR LE DASHBOARD V37 / CORRIGÉ V39.1) ---
        cols_forme = ['Ligue', 'Équipe', 'Form_Score', 'Form_Last_5_Str', 'Prochain_Match']
        if 'Form_Score' in df_rapport_complet.columns:
            df_forme = df_rapport_complet[cols_forme].copy()
            
            # --- NOUVEAU V37: Formater les pilules de forme ---
            df_forme['5 Derniers (Détails)'] = df_forme['Form_Last_5_Str'].apply(formater_forme_html) # NOUVELLE COLONNE
            
            df_forme = df_forme.rename(columns={
                'Ligue': 'Ligue',
                'Form_Score': 'Score de Forme',
                'Prochain_Match': 'Prochain Match'
            })
            df_forme = df_forme.sort_values(by='Score de Forme', ascending=False)
            
            # --- CORRECTION V39.1 ---
            cols_to_display = ['Ligue', 'Équipe', 'Score de Forme', '5 Derniers (Détails)', 'Prochain Match']
            df_forme_final = df_forme[cols_to_display] 
            
            df_top10 = df_forme_final.head(10)
            df_bottom10 = df_forme_final.tail(10).sort_values(by='Score de Forme', ascending=True)
            df_forme_display = pd.concat([df_top10, df_bottom10]).reset_index(drop=True)
            # --- FIN CORRECTION V39.1 ---

            styler_forme = df_forme_display.style.apply(colorier_forme_v22, axis=1) \
                                        .set_table_attributes('class="styled-table form-table filterable-table"') \
                                        .format({'Score de Forme': '{:+.1f}', '5 Derniers (Détails)': '{}'}) \
                                        .hide(axis="index")
            form_table_html = styler_forme.to_html()
        else:
            form_table_html = "<h3 class='no-alerts'>Données 'FTR' non trouvées pour calculer la forme.</h3>"
        
        # --- 5. Générer le Corps HTML (Onglets de stats - MODIFIÉ V39) ---
        corps_html = ""
        for nom_base, config in stats_a_afficher.items():
            id_html = config[0]
            titre_section = config[1]
            col_record = f'{nom_base}_Record'
            col_annee = f'{nom_base}_Annee_Record' # NOUVEAU V39
            col_en_cours = f'{nom_base}_EnCours'
            col_5_derniers = 'Last_5_FT_Goals' if nom_base.startswith('FT') else 'Last_5_MT_Goals'
            nom_col_5_derniers = '5 Derniers (FT)' if nom_base.startswith('FT') else '5 Derniers (MT)'
            
            if col_record not in df_rapport_complet.columns:
                print(f"Info: Statistique '{nom_base}' sautée (colonne de données source manquante).")
                continue 
            if col_5_derniers not in df_rapport_complet.columns:
                    df_rapport_complet[col_5_derniers] = "N/A"
            if col_annee not in df_rapport_complet.columns:
                    df_rapport_complet[col_annee] = "N/A"
            
            df_stat = df_rapport_complet[['Ligue', 'Équipe', col_record, col_annee, col_en_cours, col_5_derniers]].copy() # V39
            df_stat = df_stat.rename(columns={
                col_record: 'Record', 
                col_annee: 'Année Record', # NOUVEAU V39
                col_en_cours: 'Série en Cours',
                col_5_derniers: nom_col_5_derniers
            })
            df_stat = df_stat.sort_values(by='Record', ascending=False).reset_index(drop=True)
            # CORRIGÉ V39.1: 'Année Record' formaté en '{}' (texte)
            styler = df_stat.style.apply(colorier_series_v19, axis=1) \
                                .set_table_attributes('class="styled-table filterable-table"') \
                                .format({'Année Record': '{}'}) \
                                .hide(axis="index") 
            table_html = styler.to_html()
            corps_html += f"""
            <div class="section-container tab-content" id="{id_html}">
                <h2 class="section-title">{titre_section} (Toutes Ligues)</h2>
                {table_html}
            </div>
            """

        # --- NOUVEAU V35: Générer le tableau "Résultats Semaine" ---
        if df_last_week.empty:
            last_week_table_html = "<h3 class='no-alerts'>Aucun match trouvé dans les 7 derniers jours de données.</h3>"
        else:
            if 'FTHG' not in df_last_week.columns: df_last_week['FTHG'] = '?'
            if 'FTAG' not in df_last_week.columns: df_last_week['FTAG'] = '?'
            if 'HTHG' not in df_last_week.columns: df_last_week['HTHG'] = '?'
            if 'HTAG' not in df_last_week.columns: df_last_week['HTAG'] = '?'
            df_last_week['Date_str'] = df_last_week['Date'].dt.strftime('%d/%m/%Y')
            df_last_week['Score_FT'] = df_last_week['FTHG'].astype(str).str.split('.').str[0] + ' - ' + df_last_week['FTAG'].astype(str).str.split('.').str[0]
            df_last_week['Score_HT'] = '(' + df_last_week['HTHG'].astype(str).str.split('.').str[0] + ' - ' + df_last_week['HTAG'].astype(str).str.split('.').str[0] + ')'
            
            cols_to_show = ['Date_str', 'Ligue', 'HomeTeam', 'AwayTeam', 'Score_FT', 'Score_HT']
            df_week_display = df_last_week[cols_to_show].copy()
            df_week_display = df_week_display.rename(columns={
                'Date_str': 'Date', 'HomeTeam': 'Domicile', 'AwayTeam': 'Extérieur',
                'Score_FT': 'Score Final', 'Score_HT': 'Score MT'
            })
            df_week_display = df_week_display.sort_values(by='Date', ascending=False)
            styler_last_week = df_week_display.style \
                                        .set_table_attributes('class="styled-table last-week-table filterable-table"') \
                                        .hide(axis="index")
            last_week_table_html = styler_last_week.to_html()

        last_week_html = f"""
        <div class="section-container tab-content" id="last-week-section">
            <h2 class="section-title">Résultats de la Semaine Passée</h2>
            <p class="section-subtitle">Affiche tous les résultats des 7 derniers jours de données (selon les CSV).</p>
            {last_week_table_html}
        </div>
        """

        # --- NOUVEAU V33 / MODIFIÉ V34 : Générer le tableau des Séries Brisées ---
        if df_series_brisees.empty:
            broken_table_html = "<h3 class='no-alerts'>Aucune série brisée depuis la dernière exécution.</h3>"
        else:
            styler_brisees = df_series_brisees.style \
                                        .set_table_attributes('class="styled-table broken-table filterable-table"') \
                                        .hide(axis="index")
            broken_table_html = styler_brisees.to_html()

        total_suivies = count_brisees + count_actives
        if total_suivies == 0:
             summary_html = f"""
            <div class="broken-summary">
                <p>Aucune série (Rouge, Orange ou Vert) n'était active lors de la dernière exécution.</p>
                <p>(Les données s'afficheront après la prochaine mise à jour de vos CSV)</p>
            </div>
            """
        else:
            summary_html = f"""
            <div class="broken-summary">
                <p>Sur les <strong>{total_suivies}</strong> séries suivies (Rouge, Orange ou Vert) depuis la dernière exécution :</p>
                <ul>
                    <li><strong style="color: #c82333;">{count_brisees}</strong> séries ont été brisées (sont retombées à 0).</li>
                    <li><strong style="color: #2e7d32;">{count_actives}</strong> séries sont toujours actives.</li>
                </ul>
            </div>
            """

        broken_series_html = f"""
        <div class="section-container tab-content" id="broken-series-section">
            <h2 class="section-title">Séries Brisées Récemment (Toutes Ligues)</h2>
            <p class="section-subtitle">Affiche les séries qui étaient actives (Rouge, Orange, Vert) lors de la dernière exécution et qui sont maintenant terminées (retombées à 0).</p>
            {broken_table_html}
            {summary_html}
        </div>
        """

        # --- 6. Générer la Vue "Par Équipe" (MODIFIÉ V39) ---
        
        # (V39) D'abord, on crée le sélecteur de LIGUE
        liste_ligues_equipe = sorted(df_rapport_complet['Ligue'].unique())
        league_team_selector_html = '<select id="league-team-selector" onchange="populateTeamSelector(this.value);"><option value="">-- D\'abord, choisissez une ligue --</option>'
        for ligue in liste_ligues_equipe:
            league_team_selector_html += f'<option value="{ligue}">{ligue}</option>'
        league_team_selector_html += '</select>'

        # (V39) Ensuite, le sélecteur d'équipe (vide et désactivé)
        team_selector_html = '<select id="team-selector" onchange="showTeamStats(this.value);" disabled><option value="">-- Choisissez une équipe --</option></select>'
        
        team_data_json = df_rapport_complet.set_index('Équipe').to_json(orient="index", force_ascii=False)
        team_view_html = f"""
        <div class="section-container tab-content" id="team-view-section">
            <h2 class="section-title">Analyse par Équipe (Toutes Ligues)</h2>
            {league_team_selector_html}
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

        # --- NOUVEAU V37: Générer le Tableau de Bord ---
        dashboard_html = f"""
        <div class="section-container tab-content active" id="dashboard-section">
            <h2 class="section-title">Tableau de Bord</h2>
            <div class="dashboard-grid">
                <div class="dashboard-card card-red">
                    <div class="card-title">Alertes Rouges</div>
                    <div class="card-value">{count_alertes_rouges}</div>
                    <div class="card-footer">Séries au record historique</div>
                </div>
                <div class="dashboard-card card-orange">
                    <div class="card-title">Pré-Alertes (O/V)</div>
                    <div class="card-value">{count_pre_alertes}</div>
                    <div class="card-footer">Séries à R-1 ou R-2</div>
                </div>
                <div class="dashboard-card card-broken">
                    <div class="card-title">Séries Brisées</div>
                    <div class="card-value">{count_brisees}</div>
                    <div class="card-footer">Depuis la dernière exécution</div>
                </div>
                <div class="dashboard-card card-api">
                    <div class="card-title">Matchs Trouvés (API)</div>
                    <div class="card-value">{len(odds_api_dict) // 2}</div>
                    <div class="card-footer">Matchs avec cotes à venir</div>
                </div>
            </div>
            
            <h2 class="section-title" style="margin-top: 40px;">État de Forme (Toutes Ligues)</h2>
            <p class="section-subtitle">Les 10 équipes les plus en forme et les 10 moins en forme.</p>
            {form_table_html}

        </div>
        """
        
        # --- 7. Définir le Style CSS (MODIFIÉ V39) ---
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
            .main-header nav a.alert-button { background-color: #ffc107; color: #333; font-weight: bold; }
            .main-header nav a.alert-button.active { background-color: #e0a800; color: #000; }
            .main-header nav a.pre-alert-button { background-color: #f57c00; color: white; font-weight: bold; }
            .main-header nav a.pre-alert-button.active { background-color: #e65100; }
            .main-header nav a.team-button { background-color: #6f42c1; color: white; font-weight: bold; }
            .main-header nav a.team-button.active { background-color: #5a37a0; }
            .main-header nav a.broken-button { background-color: #dc3545; color: white; font-weight: bold; }
            .main-header nav a.broken-button.active { background-color: #c82333; }
            .main-header nav a.history-button { background-color: #6c757d; color: white; font-weight: bold; }
            .main-header nav a.history-button.active { background-color: #5a6268; }
            .main-header nav a.dashboard-button { background-color: #007bff; color: white; font-weight: bold; }
            .main-header nav a.dashboard-button.active { background-color: #0056b3; }
            
            .main-content {
                display: flex; justify-content: center; align-items: center;
                flex-direction: column; width: 100%; padding-top: 20px; padding-bottom: 20px;
            }
            /* --- NOUVEAU V37: Filtre de Ligue --- */
            .league-filter-container {
                width: 90%;
                max-width: 1100px;
                margin-bottom: 15px;
                display: none; /* Caché par défaut, affiché par JS */
            }
            #league-filter {
                width: 100%;
                padding: 10px;
                font-size: 1em;
                border-radius: 8px;
                border: 1px solid #ddd;
                background-color: white;
            }
            
            .section-container.tab-content {
                display: none; width: 90%; 
                max-width: 1100px; 
                margin-bottom: 20px;
            }
            /* MODIFIÉ V37: Affiche le tableau de bord par défaut */
            .section-container.tab-content.active { display: block; }
            #welcome-message { display: none; } 
            
            .no-alerts {
                text-align: center; color: #555;
                font-size: 1.2em; margin-top: 50px;
            }
            .section-title {
                color: #333; text-align: center; font-size: 1.5em; margin-bottom: 20px;
            }
            .section-subtitle {
                text-align: center; font-size: 0.9em; color: #666;
                margin-top: -15px; margin-bottom: 20px;
            }
            
            /* --- NOUVEAU V37 : Grille du Tableau de Bord --- */
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .dashboard-card {
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                text-align: center;
            }
            .dashboard-card .card-title {
                font-size: 1.1em;
                font-weight: bold;
                color: #555;
            }
            .dashboard-card .card-value {
                font-size: 3em;
                font-weight: bold;
                margin: 10px 0;
            }
            .dashboard-card .card-footer {
                font-size: 0.9em;
                color: #888;
            }
            .dashboard-card.card-red .card-value { color: #c82333; }
            .dashboard-card.card-orange .card-value { color: #f57c00; }
            .dashboard-card.card-broken .card-value { color: #dc3545; }
            .dashboard-card.card-api .card-value { color: #007bff; }

            /* --- NOUVEAU V37 : Pilules de Forme --- */
            .form-pill {
                display: inline-block;
                width: 22px;
                height: 22px;
                line-height: 22px;
                text-align: center;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                font-size: 0.8em;
                margin: 0 1px;
            }
            .form-pill.form-v { background-color: #28a745; }
            .form-pill.form-n { background-color: #ffc107; color: #333; }
            .form-pill.form-d { background-color: #dc3545; }


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
            .styled-table th:nth-child(2), .styled-table td:nth-child(2) { text-align: left; }
            
            /* (V39) Col 3+ (Stats) */
            .styled-table th:nth-child(n+3), .styled-table td:nth-child(n+3) {
                text-align: center; font-weight: bold;
            }
            /* (V39) Col 6 (5 Derniers) */
            .styled-table th:nth-child(6), .styled-table td:nth-child(6) {
                font-weight: normal; color: #777; font-size: 0.9em;
            }
            
            /* Styles pour le tableau de FORME */
            .form-table td:nth-child(1), .form-table td:nth-child(2) { font-weight: bold; } /* Ligue, Equipe */
            .form-table th:nth-child(4), .form-table td:nth-child(4) { /* 5 Derniers (Détails) */
                font-weight: normal; font-size: 0.9em;
            }
            .form-table th:nth-child(5), .form-table td:nth-child(5) { /* Prochain Match */
                font-weight: normal; color: #17a2b8; font-size: 0.9em;
            }
            
            .styled-table tbody tr {
                border-bottom: 1px solid #dddddd; background-color: #ffffff;
            }
            .styled-table tbody tr:nth-of-type(even) { background-color: #f8f8f8; }
            
            /* (V39) Styles pour le tableau d'ALERTES */
            .alerts-table td { font-weight: bold !important; }
            .alerts-table td:nth-child(1) { /* Ligue */
                font-weight: normal !important; 
                font-size: 0.9em; text-align: left;
            }
            .alerts-table td:nth-child(5) { /* Année Record */
                font-weight: normal !important; 
                font-size: 0.9em; text-align: center;
            }
            .alerts-table td:nth-child(7) { /* 5 Derniers Buts */
                font-weight: normal !important; 
                font-size: 0.9em;
            }
            .alerts-table td:nth-child(8) { /* Prochain Match */
                font-weight: normal !important; 
                color: #17a2b8; font-size: 0.9em;
            }
            .alerts-table td:nth-child(9) { /* Cote (Pari Inverse) */
                font-weight: bold !important; 
                color: #0056b3; font-size: 1.05em; text-align: center;
            }

            /* Styles pour le tableau "Séries Brisées" */
            .broken-table td:nth-child(1), .broken-table td:nth-child(2) { /* Ligue, Equipe */
                font-weight: bold;
            }
            .broken-table td:nth-child(3) { /* Statistique */
                 font-weight: normal; color: #dc3545;
            }
            .broken-table td:nth-child(4) { /* Série Précédente */
                font-weight: bold; text-align: center;
            }
            
            /* Style pour le résumé des séries brisées */
            .broken-summary {
                margin-top: 25px;
                padding: 20px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                text-align: center;
            }
            .broken-summary p {
                font-size: 1.1em;
                font-weight: bold;
                margin-top: 0;
            }
            .broken-summary ul {
                list-style: none;
                padding-left: 0;
                margin-bottom: 0;
                text-align: center;
                font-size: 1em;
            }
            .broken-summary li {
                margin: 5px 0;
            }

            /* Styles pour le tableau "Résultats Semaine" */
            .last-week-table td {
                text-align: left;
                font-weight: bold;
                font-size: 0.95em;
            }
            .last-week-table td:nth-child(1), .last-week-table td:nth-child(2) { /* Date, Ligue */
                font-weight: normal;
                font-size: 0.9em;
                color: #555;
            }
            .last-week-table td:nth-child(5), .last-week-table td:nth-child(6) { /* Score FT, Score HT */
                text-align: center;
                font-family: "Courier New", Courier, monospace;
            }
            .last-week-table td:nth-child(5) { /* Score FT */
                 font-size: 1.1em;
            }
             .last-week-table td:nth-child(6) { /* Score HT */
                 font-size: 0.9em;
                 color: #777;
            }

            /* --- NOUVEAU V39 : Style pour les sélecteurs par équipe --- */
            #league-team-selector {
                width: 100%;
                padding: 12px;
                font-size: 1.1em;
                border-radius: 8px;
                border: 1px solid #ddd;
                background-color: white;
                margin-bottom: 10px; /* Ajout d'une marge */
            }
            #team-selector {
                width: 100%;
                padding: 12px;
                font-size: 1.1em;
                border-radius: 8px;
                border: 1px solid #ddd;
                background-color: white;
                margin-bottom: 25px;
            }
            #team-selector:disabled {
                background-color: #f8f8f8;
                color: #999;
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
            /* (V39) Style pour la nouvelle info Année Record */
            .team-stats-table .annee-record {
                font-size: 0.85em;
                font-weight: normal;
                color: #888;
                margin-left: 5px;
            }
            .team-stats-table td:last-child {
                text-align: right;
                font-weight: bold;
                font-size: 1.05em;
            }
        </style>
        """

        # --- 8. Le SCRIPT JAVASCRIPT (MODIFIÉ V39) ---
        javascript_code = """
        <script>
            // --- NOUVEAU V37: Map pour les pilules de forme ---
            const formPillMapping = {
                'V': '<span class="form-pill form-v">V</span>',
                'N': '<span class="form-pill form-n">N</span>',
                'D': '<span class="form-pill form-d">D</span>',
            };

            function showSection(sectionId, clickedLink) {
                // (MODIFIÉ V37) Gérer l'affichage du filtre de ligue
                const filterContainer = document.getElementById('league-filter-container');
                if (sectionId === 'team-view-section' || sectionId === 'dashboard-section') {
                    filterContainer.style.display = 'none';
                } else {
                    filterContainer.style.display = 'block';
                }
                
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

            // --- NOUVEAU V37: Fonction pour filtrer les tableaux par ligue (CORRIGÉ V38) ---
            function filterTablesByLeague(selectedLeague) {
                const tables = document.querySelectorAll('.filterable-table');
                
                tables.forEach(table => {
                    const rows = table.querySelectorAll('tbody tr');

                    // --- DEBUT DE LA CORRECTION V38 ---
                    // On détermine quelle colonne contient la Ligue
                    let colIndex = 0; // Par défaut, la 1ère colonne (index 0)
                    
                    if (table.classList.contains('last-week-table')) {
                        colIndex = 1; // Pour "Résultats Semaine", c'est la 2ème colonne (index 1)
                    }
                    // --- FIN DE LA CORRECTION V38 ---

                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length <= colIndex) return; // Sécurité
                        
                        // On utilise le bon index de colonne
                        const leagueCell = cells[colIndex]; 
                        const leagueName = leagueCell.innerText;
                        
                        if (selectedLeague === 'Toutes' || leagueName === selectedLeague) {
                            row.style.display = ''; // Afficher la ligne
                        } else {
                            row.style.display = 'none'; // Cacher la ligne
                        }
                    });
                });
            }

            // --- NOUVEAU V37: Helper JS pour convertir "V,D,N" en pilules ---
            function formatFormString(formStr) {
                if (!formStr || formStr === "N/A") return "N/A";
                return formStr.split(',')
                              .map(r => formPillMapping[r.trim()] || r)
                              .join(' ');
            }
            
            // --- NOUVEAU V39: Fonction pour peupler le sélecteur d'équipe ---
            function populateTeamSelector(selectedLeague) {
                const teamSelector = document.getElementById('team-selector');
                const alertsContainer = document.getElementById('team-alerts-output');
                const statsContainer = document.getElementById('team-stats-output');
                
                // Vider tout
                teamSelector.innerHTML = '<option value="">-- Choisissez une équipe --</option>';
                alertsContainer.innerHTML = "";
                statsContainer.innerHTML = "";

                if (!selectedLeague) {
                    teamSelector.disabled = true;
                    return;
                }

                const teamData = JSON.parse(document.getElementById('team-data-json').textContent);
                let teamsInLeague = [];
                for (const teamName in teamData) {
                    if (teamData[teamName].Ligue === selectedLeague) {
                        teamsInLeague.push(teamName);
                    }
                }

                teamsInLeague.sort();
                teamsInLeague.forEach(teamName => {
                    teamSelector.innerHTML += `<option value="${teamName}">${teamName}</option>`;
                });

                teamSelector.disabled = false;
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
                
                // (MODIFIÉ V39) Appelle formatFormString et ajoute l'année record
                let statsHtml = "<h3>Toutes les Caractéristiques</h3>";
                statsHtml += '<table class="team-stats-table"><tbody>';
                statsHtml += `<tr><td>Ligue</td><td>${stats.Ligue || 'N/A'}</td></tr>`;
                statsHtml += `<tr><td>Prochain Match</td><td>${stats.Prochain_Match || 'N/A'}</td></tr>`;
                statsHtml += `<tr><td>Score de Forme</td><td>${stats.Form_Score !== undefined ? stats.Form_Score.toFixed(1) : 'N/A'}</td></tr>`;
                statsHtml += `<tr><td>Détails 5 Derniers</td><td>${formatFormString(stats.Form_Last_5_Str)}</td></tr>`;
                statsHtml += `<tr><td>5 Derniers Buts (FT)</td><td>${stats.Last_5_FT_Goals || 'N/A'}</td></tr>`;
                statsHtml += `<tr><td>5 Derniers Buts (MT)</td><td>${stats.Last_5_MT_Goals || 'N/A'}</td></tr>`;
                for (const statName in STATS_CONFIG) {
                     const annee_record_val = stats[statName + '_Annee_Record'] || 'N/A';
                     const record_val = stats[statName + '_Record'] || 'N/A';
                     const annee_str = (annee_record_val !== 'N/A' && annee_record_val !== null) ? `(${annee_record_val})` : '';
                     
                     statsHtml += `<tr>
                        <td>${statName} (Record)</td>
                        <td>${record_val} <span class="annee-record">${annee_str}</span></td>
                     </tr>`;
                     statsHtml += `<tr>
                        <td>${statName} (Série)</td>
                        <td>${stats[statName + '_EnCours']}</td>
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
                // (MODIFIÉ V37) Appliquer le tri à TOUS les tableaux
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

        # --- 9. Assembler le HTML Final (MODIFIÉ V38) ---
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
            
                <div class="league-filter-container" id="league-filter-container">
                    {filtre_ligue_html}
                </div>
                
                {dashboard_html}
                
                {last_week_html}
                
                {broken_series_html}
                
                {team_view_html}
                
                <div class="section-container tab-content" id="alert-section">
                    <h2 class="section-title">TABLEAU DES ALERTES ROUGES (Toutes Ligues)</h2>
                    {alert_table_html}
                </div>
                
                <div class="section-container tab-content" id="pre-alert-section">
                    <h2 class="section-title">TABLEAU DES PRÉ-ALERTES (Orange/Vert)</h2>
                    {pre_alert_table_html}
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
        
        print(f"\nSuccès ! Le rapport V39.1 pour {titre_rapport} a été généré ici : {os.path.abspath(nom_fichier_html)}")

    except Exception as e:
        print(f"\nErreur lors de la génération du fichier HTML : {e}")


# --- (MODIFIÉ V41) FONCTION DE CHARGEMENT V41 ---
def charger_donnees(fichiers_csv):
    """
    Charge et combine tous les fichiers CSV.
    MODIFIÉ V41: Charge et parse les dates fichier par fichier avant de combiner,
                 pour gérer les formats de date mixtes.
                 Remplace .dropna() par .fillna() pour ne pas casser
                 les séries en cas de données manquantes (scores OU FTR).
    """
    all_dfs = []
    print(f"Chargement de {len(fichiers_csv)} fichiers...")
    
    for f in fichiers_csv:
        league_code = os.path.basename(f).replace('.csv', '')
        try:
            df_temp = pd.read_csv(f, on_bad_lines='skip')
        except UnicodeDecodeError:
            print(f"  Avertissement: Échec UTF-8 pour {os.path.basename(f)}. Tentative avec 'latin1'...")
            try:
                df_temp = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
            except Exception as e_latin:
                print(f"  ERREUR: Impossible de charger {os.path.basename(f)} avec UTF-8 ou latin1. Erreur : {e_latin}")
                continue # Passer au fichier suivant
        except Exception as e:
            print(f"  ERREUR: Impossible de charger {os.path.basename(f)}. Erreur : {e}")
            continue # Passer au fichier suivant

        # --- NOUVELLE LOGIQUE DE DATE V41 ---
        # Essayer de parser la date avec 'dayfirst=True'
        df_temp['Date'] = pd.to_datetime(df_temp['Date'], dayfirst=True, errors='coerce')
        
        # Si TOUTES les dates ont échoué, essayer avec 'dayfirst=False' (format US)
        if df_temp['Date'].isna().all():
            print(f"  - Info: Format de date 'dayfirst=True' a échoué pour {os.path.basename(f)}. Tentative avec format US.")
            # Re-lire le fichier pour ne pas avoir de dates partielles
            try:
                df_temp = pd.read_csv(f, on_bad_lines='skip')
            except: # Gérer les erreurs d'encodage à nouveau
                try:
                    df_temp = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
                except:
                    continue # Echec total
            
            df_temp['Date'] = pd.to_datetime(df_temp['Date'], dayfirst=False, errors='coerce')
        # --- FIN LOGIQUE DE DATE V41 ---
            
        df_temp['LeagueCode'] = league_code 
        all_dfs.append(df_temp)
            
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

    # (V41) On ne supprime que les lignes où les infos de base sont manquantes
    df = df.dropna(subset=colonnes_base) 
    
    # (V41) On ne supprime que les lignes où la DATE est TOUJOURS invalide
    df = df.dropna(subset=['Date'])
    df = df.sort_values(by='Date')
    
    # --- PRÉ-CALCUL DE TOUTES LES CONDITIONS (CORRIGÉ V41) ---
    # On remplace les NaN par 0 (pour les scores) ou 'NA' (pour FTR)
    # au lieu de supprimer les lignes, pour préserver l'historique des séries.
    
    if 'FTHG' in df.columns and 'FTAG' in df.columns:
        df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce').fillna(0)
        df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce').fillna(0)
        
        df['TotalGoals'] = df['FTHG'] + df['FTAG']
        df['Cond_Moins_0_5_FT'] = df['TotalGoals'] < 0.5   # 0
        df['Cond_Plus_1_5_FT']  = df['TotalGoals'] > 1.5   # 2+
        df['Cond_Moins_1_5_FT'] = df['TotalGoals'] < 1.5   # 0-1
        df['Cond_Plus_2_5_FT']  = df['TotalGoals'] > 2.5   # 3+
        df['Cond_Moins_2_5_FT'] = df['TotalGoals'] < 2.5   # 0-2
        df['Cond_Plus_3_5_FT']  = df['TotalGoals'] > 3.5   # 4+
        df['Cond_Moins_3_5_FT'] = df['TotalGoals'] < 3.5   # 0-3
    
    if 'HTHG' in df.columns and 'HTAG' in df.columns:
        df['HTHG'] = pd.to_numeric(df['HTHG'], errors='coerce').fillna(0)
        df['HTAG'] = pd.to_numeric(df['HTAG'], errors='coerce').fillna(0)
        
        df['TotalHTGoals'] = df['HTHG'] + df['HTAG']
        df['Cond_Plus_0_5_HT']  = df['TotalHTGoals'] > 0.5 # 1+ MT
        df['Cond_Moins_0_5_HT'] = df['TotalHTGoals'] < 0.5 # 0 MT
        df['Cond_Plus_1_5_HT']  = df['TotalHTGoals'] > 1.5 # 2+ MT
        df['Cond_Moins_1_5_HT'] = df['TotalHTGoals'] < 1.5 # 0-1 MT
        
    if 'FTR' in df.columns:
        df['FTR'] = df['FTR'].fillna('NA') # Remplacer FTR manquant par 'NA'
        df['Cond_Draw_FT'] = df['FTR'] == 'D' 
    
    print("Toutes les données ont été préparées et les conditions pré-calculées.")
    return df

# --- (MODIFIÉ V39) Fonction Helper ---
def trouver_max_serie_pour_colonne(df_equipe, nom_colonne_condition):
    """
    Helper: Calcule la série max pour une colonne de condition.
    (V39) Renvoie (max_streak, annee_record)
    """
    if nom_colonne_condition not in df_equipe.columns or 'Date' not in df_equipe.columns:
        return 0, "N/A" # Retourne un tuple
        
    df_equipe = df_equipe.sort_values(by='Date')
    df_equipe['streak_group'] = (df_equipe[nom_colonne_condition] != df_equipe[nom_colonne_condition].shift()).cumsum()
    streaks_when_true = df_equipe[df_equipe[nom_colonne_condition] == True]

    if streaks_when_true.empty:
        max_streak = 0
        annee_record = "N/A"
    else:
        streak_lengths = streaks_when_true.groupby('streak_group').size()
        max_streak = int(streak_lengths.max())
        
        # --- NOUVEAU V39: Trouver l'année ---
        groupes_max = streak_lengths[streak_lengths == max_streak].index
        dates_de_fin = []
        for group_id in groupes_max:
            if group_id in streaks_when_true['streak_group'].values:
                date_fin = streaks_when_true[streaks_when_true['streak_group'] == group_id]['Date'].max()
                dates_de_fin.append(date_fin)
        
        dates_valides = [d for d in dates_de_fin if pd.notna(d)]
        if not dates_valides:
            annee_record = "N/A"
        else:
            date_fin_record_recente = max(dates_valides)
            annee_record = date_fin_record_recente.year
        # --- FIN NOUVEAU V39 ---
            
    return max_streak, annee_record # Retourne un tuple

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


# --- (MODIFIÉ V41) FONCTION HELPER (V29 - Forme simplifiée) ---
def calculer_score_de_forme(df_equipe, equipe):
    """
    Calcule le score de forme pondéré sur les 5 derniers matchs.
    MODIFIÉ V41: Ne plante pas si 'FTR' est manquant, filtre 'NA'.
    """
    if 'FTR' not in df_equipe.columns or 'FTHG' not in df_equipe.columns:
        return 0, "N/A" # Impossible de calculer
    
    # V41: On ne peut pas utiliser les lignes avec FTR='NA'
    df_equipe_forme = df_equipe[df_equipe['FTR'] != 'NA'].copy()
    
    df_equipe_forme = df_equipe_forme.sort_values(by='Date')
    last_5_games = df_equipe_forme.tail(5)
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


# --- (MODIFIÉ V39) FONCTION DE CALCUL V39 ---
def calculer_tous_les_records_et_series(df, ligues_a_analyser, odds_api_dict):
    """
    Calcule le RECORD, l'ANNÉE RECORD, la SÉRIE EN COURS, etc.
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
    
    # --- NOUVELLE BOUCLE V32 ---
    for code_ligue, equipes in ligues_a_analyser.items():
        nom_ligue_lisible = LEAGUE_NAME_MAPPING.get(code_ligue, code_ligue)
        print(f"  -> Traitement de {nom_ligue_lisible}...")
        
        for equipe in equipes:
            df_equipe = df[
                (df['HomeTeam'] == equipe) | (df['AwayTeam'] == equipe)
            ].copy()
            if df_equipe.empty: continue
            
            # --- NOUVEAU V32: Ajout de la Ligue ---
            record_equipe = {'Équipe': equipe, 'Ligue': nom_ligue_lisible}
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
                start_time_iso = match_info.get('commence_time')
                try:
                    utc_date = pd.to_datetime(start_time_iso)
                    date_str = utc_date.strftime('%d/%m %H:%M')
                except:
                    date_str = "Date?"
                prochain = f"{date_str} -> {opponent} ({loc_str})"
            
            record_equipe['Prochain_Match'] = prochain
            # --- FIN MODIFICATION V31 ---
                
            for nom_base, nom_col_data in conditions_a_tester.items():
                # --- MODIFIÉ V39: Récupérer (record, annee) ---
                record, annee_record = trouver_max_serie_pour_colonne(df_equipe, nom_col_data)
                record_equipe[f'{nom_base}_Record'] = record
                record_equipe[f'{nom_base}_Annee_Record'] = annee_record # NOUVEAU V39
                
                en_cours = trouver_serie_en_cours_pour_colonne(df_equipe, nom_col_data)
                record_equipe[f'{nom_base}_EnCours'] = en_cours
                
            resultats.append(record_equipe)
            
    df_rapport_final = pd.DataFrame(resultats)
    df_rapport_final = df_rapport_final.sort_values(by=['Ligue', 'Équipe']).reset_index(drop=True)
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


# --- (SUPPRIMÉ V32) Ancienne fonction creer_page_hub ---


# --- (NOUVEAU V34) FONCTION POUR COMPARER LE CACHE ---
def analyser_cache_series(df_actuel, df_cache):
    """
    Compare le rapport actuel au cache pour trouver les séries brisées
    et les séries toujours actives.
    Retourne : (df_brisees, count_brisees, count_actives)
    """
    print("Comparaison avec le cache pour trouver les séries brisées...")
    if df_cache.empty:
        print("  - Fichier cache non trouvé ou vide. Aucune série brisée ne peut être calculée.")
        return pd.DataFrame(columns=['Ligue', 'Équipe', 'Statistique', 'Série Précédente']), 0, 0
        
    try:
        # Fusionner les anciens et nouveaux résultats
        df_merged = pd.merge(
            df_actuel, 
            df_cache, 
            on=['Ligue', 'Équipe'], 
            suffixes=('_actuel', '_cache'),
            how='left' # Garder toutes les équipes actuelles
        )
        
        brisees = []
        actives_encore = [] # <-- NOUVEAU V34
        
        for stat in STATS_COLUMNS_BASE:
            col_actuel = f'{stat}_EnCours_actuel'
            col_cache = f'{stat}_EnCours_cache'
            
            # S'assurer que les colonnes existent (au cas où le cache est ancien/invalide)
            if col_actuel not in df_merged.columns or col_cache not in df_merged.columns:
                print(f"  - Avertissement: Colonne {stat} non trouvée dans le cache. Ignorée.")
                continue

            # Remplir les NaN (nouvelles équipes) avec 0 pour le cache
            df_merged[col_cache] = df_merged[col_cache].fillna(0)

            # Condition 1: Série est brisée
            # (Était > 0, est maintenant == 0)
            condition_brisee = (df_merged[col_cache] > 0) & (df_merged[col_actuel] == 0)
            df_brisees_stat = df_merged[condition_brisee]
            
            for index, row in df_brisees_stat.iterrows():
                brisees.append({
                    'Ligue': row['Ligue'],
                    'Équipe': row['Équipe'],
                    'Statistique': stat,
                    'Série Précédente': int(row[col_cache])
                })
                
            # --- NOUVEAU V34 ---
            # Condition 2: Série est toujours active
            # (Était > 0, est toujours > 0)
            condition_active = (df_merged[col_cache] > 0) & (df_merged[col_actuel] > 0)
            df_actives_stat = df_merged[condition_active]
            actives_encore.extend(df_actives_stat.to_dict('records'))
            # --- FIN NOUVEAU V34 ---
        
        count_brisees = len(brisees)
        count_actives = len(actives_encore)

        if not brisees:
            print("  - Aucune série brisée détectée.")
            df_final_brisees = pd.DataFrame(columns=['Ligue', 'Équipe', 'Statistique', 'Série Précédente'])
        else:
            df_final_brisees = pd.DataFrame(brisees)
            df_final_brisees = df_final_brisees.sort_values(by=['Ligue', 'Équipe', 'Série Précédente'], ascending=[True, True, False])
        
        print(f"  - {count_brisees} séries brisées trouvées.")
        print(f"  - {count_actives} séries sont toujours actives.")
        
        return df_final_brisees, count_brisees, count_actives

    except Exception as e:
        print(f"  - ERREUR lors de la comparaison du cache : {e}")
        print("  - Le cache est peut-être corrompu ou d'une ancienne version. Il sera écrasé.")
        return pd.DataFrame(columns=['Ligue', 'Équipe', 'Statistique', 'Série Précédente']), 0, 0


# --- (NOUVEAU V40) FONCTION POUR NOTIFICATION DISCORD ---
def envoyer_notifications_discord(alertes_rouges, webhook_url):
    """
    Envoie un message Discord formaté avec toutes les alertes rouges.
    """
    if not alertes_rouges:
        print("  - Aucune alerte rouge à notifier.")
        return
        
    print(f"Envoi de {len(alertes_rouges)} notifications vers Discord...")
    
    # Créer un message formaté
    message_description = ""
    for alerte in alertes_rouges:
        message_description += f"**{alerte['Équipe']}** ({alerte['Ligue']}) : **{alerte['Statistique']}** (Série: **{alerte['Série en Cours']}**)\n"

    # Limiter la longueur du message (limite Discord de 2000 caractères)
    if len(message_description) > 1900:
        message_description = message_description[:1900] + "\n... et plus encore."

    # Préparer le "payload" JSON pour Discord
    data = {
        "content": f"🚨 **{len(alertes_rouges)} Alertes Rouges Détectées !** 🚨", # Titre principal
        "embeds": [
            {
                "title": "Rapport des Séries au Record",
                "description": message_description,
                "color": 15158332, # Couleur rouge
                "footer": {
                    "text": f"Analyse effectuée le {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
                }
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status() # Lèvera une erreur si le code est 4xx ou 5xx
        print("  - Notifications Discord envoyées avec succès.")
    except requests.exceptions.RequestException as e:
        print(f"  - ERREUR: Impossible d'envoyer la notification Discord. {e}")


# --- POINT D'ENTRÉE DU SCRIPT (MODIFIÉ V40) ---
if __name__ == "__main__":
    
    SAISON_API = 2025 
    dossier_csv_principal = "CSV_Data" 
    
    fichier_cache = "rapport_cache.csv"
    
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
    
    # 4. Charger les COTES & MATCHS via 'The Odds API'
    if not hasattr(config, 'API_KEY'):
        print("\nERREUR: 'API_KEY' non trouvée dans config.py. Arrêt.")
        print("Veuillez mettre votre clé 'The Odds API' dans config.py.")
        exit()
        
    odds_api_dict = charger_cotes_via_api(
        config.API_KEY, 
        ligues_a_analyser.keys()
    )
    
    if donnees_completes is not None:
        
        print(f"\n--- DÉBUT DU TRAITEMENT GLOBAL ---")

        # 5. Calculer tous les records pour TOUTES les ligues en une fois
        df_rapport_global = calculer_tous_les_records_et_series(
            donnees_completes, 
            ligues_a_analyser,  # On passe le dict de ligues
            odds_api_dict       # Dico API Cotes (seule source)
        )

        # 6. Étape (Affichage console)
        print(f"\n--- RÉSULTAT GLOBAL (Aperçu) ---")
        pd.set_option('display.max_rows', 5) # Afficher un aperçu
        print(df_rapport_global)
        pd.reset_option('display.max_rows')
        
        # --- NOUVEAU V40: Filtrer les alertes rouges pour Discord ---
        print("Filtrage des alertes rouges pour notification Discord...")
        alertes_rouges_discord = []
        for stat in STATS_COLUMNS_BASE:
            col_record = f'{stat}_Record'
            col_en_cours = f'{stat}_EnCours'
            
            # Condition: Série en cours > 0 ET Série en cours == Record
            condition_rouge = (df_rapport_global[col_en_cours] > 0) & (df_rapport_global[col_en_cours] == df_rapport_global[col_record])
            
            df_alertes_stat = df_rapport_global[condition_rouge]
            
            for index, row in df_alertes_stat.iterrows():
                alertes_rouges_discord.append({
                    'Ligue': row['Ligue'],
                    'Équipe': row['Équipe'],
                    'Statistique': stat,
                    'Série en Cours': int(row[col_en_cours])
                })

        if alertes_rouges_discord:
            print(f"  - {len(alertes_rouges_discord)} alertes rouges trouvées.")
            if hasattr(config, 'DISCORD_WEBHOOK_URL') and "VOTRE_URL" not in config.DISCORD_WEBHOOK_URL and config.DISCORD_WEBHOOK_URL != "":
                envoyer_notifications_discord(alertes_rouges_discord, config.DISCORD_WEBHOOK_URL)
            else:
                print("  - Avertissement: 'DISCORD_WEBHOOK_URL' non configurée dans config.py. Notifications sautées.")
        else:
            print("  - Aucune alerte rouge à notifier.")
        # --- FIN NOUVEAU V40 ---

        
        # 7. (NOUVEAU V35) Filtrer les résultats de la semaine passée
        print("Filtrage des résultats de la semaine passée...")
        df_last_week = pd.DataFrame() # Initialiser
        if 'Date' in donnees_completes.columns and not donnees_completes.empty:
            date_max = donnees_completes['Date'].max()
            date_min = date_max - pd.Timedelta(days=7)
            df_last_week = donnees_completes[(donnees_completes['Date'] > date_min) & (donnees_completes['Date'] <= date_max)].copy()
            
            # Ajouter le nom lisible de la ligue
            if not df_last_week.empty:
                df_last_week['Ligue'] = df_last_week['LeagueCode'].map(LEAGUE_NAME_MAPPING).fillna(df_last_week['LeagueCode'])
        
        # 8. (NOUVEAU V34) Charger l'ancien cache et comparer
        df_cache = pd.DataFrame() 
        try:
            if os.path.exists(fichier_cache):
                df_cache = pd.read_csv(fichier_cache)
        except Exception as e:
            print(f"Avertissement: Impossible de lire le fichier cache '{fichier_cache}'. Il sera recréé. Erreur: {e}")

        df_series_brisees, count_brisees, count_actives = analyser_cache_series(df_rapport_global, df_cache)
        
        # 9. ÉTAPE 5 : SAUVEGARDE EN UN SEUL FICHIER HTML
        nom_du_fichier_html = "index.html" # On sauvegarde directement en index.html
        titre_rapport = "Rapport Global des Ligues"
        
        # (MODIFIÉ V38)
        sauvegarder_rapport_global_html(
            df_rapport_global, 
            df_series_brisees, 
            count_brisees,
            count_actives,
            df_last_week,
            nom_du_fichier_html, 
            titre_rapport,
            odds_api_dict 
        )
        
        # 10. (NOUVEAU V33) Sauvegarder les résultats actuels dans le cache pour la prochaine fois
        try:
            df_rapport_global.to_csv(fichier_cache, index=False)
            print(f"Succès : Le cache des séries a été mis à jour dans '{fichier_cache}'.")
        except Exception as e:
            print(f"ERREUR: Impossible de sauvegarder le cache dans '{fichier_cache}'. Erreur: {e}")
        
        print("\n--- TRAITEMENT TERMINÉ ---")
        print(f"Le rapport global '{nom_du_fichier_html}' a été créé.")
        
    else:
        print("Erreur : Le chargement des données a échoué. Le script s'arrête.")