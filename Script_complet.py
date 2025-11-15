import pandas as pd
import numpy as np
import glob # Pour lire les fichiers dans un dossier
import os   # Pour gérer les noms de fichiers
import re   # Pour les noms de dossiers
import requests # Pour les requêtes API
import config   # Pour charger votre clé
import time     # Pour les pauses API (si nécessaire)
import datetime

# ##########################################################################
# --- Dictionnaire de Traduction des Ligues ---
# ##########################################################################
LEAGUE_NAME_MAPPING = {
    'E0': 'Premier League',
    'E1': 'Championship',
    'D1': 'Bundesliga',
    'D2': 'Bundesliga 2',
    'F1': 'Ligue 1',
    'F2': 'Ligue 2',
    'I1': 'Serie A',
    'I2': 'Serie B',
    'SP1': 'La Liga',
    'SP2': 'La Liga 2',
    'N1': 'Eredivisie (Pays-Bas)',
    'P1': 'Liga (Portugal)',
    'T1': 'Süper Lig (Turquie)',
    'G1': 'Super League (Grèce)',
    'SC0': 'Scottish Premiership',
    'B1': 'Jupiler Pro League (Belgique)',
    'X0': 'NomParDefaut' 
}

# ##########################################################################
# --- Dictionnaire de Mapping API (V25 - API-FOOTBALL) ---
# ##########################################################################
LEAGUE_API_MAPPING = {
    'E0': 39,    # Premier League
    'E1': 40,    # Championship
    'D1': 78,    # Bundesliga
    'D2': 79,    # Bundesliga 2
    'F1': 61,    # Ligue 1
    'F2': 62,    # Ligue 2
    'I1': 135,   # Serie A
    'I2': 136,   # Serie B
    'SP1': 140,  # La Liga
    'SP2': 141,  # La Liga 2
    'N1': 88,    # Eredivisie (Pays-Bas)
    'P1': 94,    # Liga (Portugal)
    'SC0': 179,  # Scottish Premiership
    'B1': 144,   # Jupiler Pro League (Belgique)
    'T1': 203,   # Süper Lig (Turquie) 
    'G1': 197    # Super League (Grèce) 
}

# ##########################################################################
# --- (V26) Dictionnaire de Mapping Cotes/Alertes ---
# ##########################################################################
# Lie la STATISTIQUE DE L'ALERTE (ex: 'FT -2.5')
# à la COLONNE DE COTE OPPOSÉE (ex: 'B365>2.5')
#
# !! ATTENTION !!
# Adaptez les noms de colonnes (ex: 'B365>3.5') pour qu'ils 
# correspondent EXACTEMENT à votre fichier 'fixtures.csv'
# (ex: 'P>3.5', 'Max>3.5', etc.)
# ##########################################################################
STAT_TO_ODD_COLUMN_MAP = {
    # Alerte sur "Plus de..." -> Parier sur "Moins de..."
    'FT +1.5': 'B365<1.5', # Vérifiez si cette colonne existe
    'FT +2.5': 'B365<2.5', # (ou 'P<2.5', 'Max<2.5')
    'FT +3.5': 'B365<3.5', # Vérifiez si cette colonne existe

    # Alerte sur "Moins de..." -> Parier sur "Plus de..."
    'FT -0.5': 'B365>0.5', # Vérifiez si cette colonne existe
    'FT -1.5': 'B365>1.5', # Vérifiez si cette colonne existe
    'FT -2.5': 'B365>2.5', # (ou 'P>2.5', 'Max>2.5')
    'FT -3.5': 'B365>3.5', # Vérifiez si cette colonne existe
    
    # Vous pouvez ajouter vos propres mappings ici
    # 'FT CS': 'B365_BTTS_Yes', # Si vous avez les cotes BTTS
}
# ##########################################################################


# --- Helper 1: Style pour les 13 tableaux de séries (4 colonnes) ---
def colorier_series_v19(row):
    """
    Applique un style aux 4 colonnes (Équipe, Record, Série, 5 Derniers).
    """
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
    """
    Applique un style à la ligne du tableau d'alertes (V22).
    MODIFIÉ V26 : Gère 8 colonnes (avec 'Cote')
    """
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
    
    # Le tableau a 8 colonnes (Équipe, Stat, Record, Série, 5 Derniers, Prochain Match, COTE, Alerte)
    return [style_base, style_base, style_base, style_base, style_5_derniers, style_prochain_match, style_base, style_base]

# --- Helper 3: Style pour le tableau de Forme (4 colonnes) ---
def colorier_forme_v22(row):
    """
    Colore le Score de Forme en fonction de sa valeur (positif/négatif).
    """
    score = row['Score de Forme']
    
    style_equipe = ''
    style_score = ''
    style_details = 'font-weight: normal; color: #777; font-size: 0.9em;'
    style_prochain_match = 'font-weight: normal; color: #17a2b8; font-size: 0.9em;'
    
    if score > 10: # Très en forme
        style_score = 'color: #2e7d32; font-weight: bold;'
    elif score > 0: # En forme
        style_score = 'color: #28a745;'
    elif score < -5: # Très méforme
        style_score = 'color: #c62828; font-weight: bold;'
    elif score < 0: # Méforme
        style_score = 'color: #dc3545;'
    
    return [style_equipe, style_score, style_details, style_prochain_match]


# --- Helper 4: Génération de la page HTML (MODIFIÉ V26) ---
def sauvegarder_en_html_v22(df_rapport_complet, nom_fichier_html, titre_rapport, fixtures_dict):
    """
    Sauvegarde le DataFrame en 14 onglets + 1 onglet "Alertes" + 1 onglet "Forme".
    MODIFIÉ V26: Accepte 'fixtures_dict' pour rechercher les cotes.
    """
    
    # 1. Définir les 14 statistiques de SÉRIE
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
        # --- 2. Générer la Barre de Navigation ---
        nav_links = ""
        nav_links += '<a href="#" onclick="showSection(\'form-section\', this); event.preventDefault();" class="form-button">📈 Forme</a>\n'
        nav_links += '<a href="#" onclick="showSection(\'alert-section\', this); event.preventDefault();" class="alert-button">⚠️ Alertes</a>\n'
        for nom_base, config in stats_a_afficher.items():
            id_html = config[0]
            nav_links += f'<a href="#" onclick="showSection(\'{id_html}\', this); event.preventDefault();">{nom_base}</a>\n'

        # --- 3. Générer le tableau d'alertes (MODIFIÉ V26) ---
        alertes_collectees = []
        for nom_base, config in stats_a_afficher.items():
            col_record = f'{nom_base}_Record'
            col_en_cours = f'{nom_base}_EnCours'
            col_5_derniers = 'Last_5_FT_Goals' if nom_base.startswith('FT') else 'Last_5_MT_Goals'
            
            for index, row in df_rapport_complet.iterrows():
                equipe = row['Équipe']
                
                if col_record not in row or pd.isna(row[col_record]):
                    continue
                    
                record = row[col_record]
                en_cours = row[col_en_cours]
                cinq_derniers_str = row.get(col_5_derniers, "N/A")
                prochain_match_str = row.get('Prochain_Match', "N/A")
                
                alerte_type = None
                if en_cours > 0 and en_cours == record: alerte_type = 'Rouge'
                elif en_cours > 0 and en_cours == record - 1: alerte_type = 'Orange'
                elif en_cours > 0 and en_cours == record - 2: alerte_type = 'Vert'
                
                if alerte_type:
                    
                    # --- NOUVEAU V26 : LOGIQUE DE RECHERCHE DE COTE ---
                    cote_pari = "N/A"
                    # 1. Trouver la colonne de cote opposée (ex: 'FT -3.5' -> 'B365>3.5')
                    nom_col_cote = STAT_TO_ODD_COLUMN_MAP.get(nom_base)
                    
                    if nom_col_cote:
                        # 2. Trouver le match de l'équipe dans le dict fixtures
                        match_info = fixtures_dict.get(equipe)
                        
                        if match_info:
                            # 3. Trouver la cote spécifique pour ce match
                            cote = match_info['odds'].get(nom_col_cote)
                            if cote:
                                cote_pari = f"{cote:.2f}" # Formaté en 2 décimales
                            else:
                                # La cote n'existe pas dans le CSV (ex: 'B365>3.5' manque)
                                cote_pari = f"({nom_col_cote}?)" 
                        else:
                             # L'équipe n'a pas de match dans fixtures.csv
                            cote_pari = "(Match?)"
                    else:
                        # La stat (ex: 'FT Nuls') n'est pas dans le MAP
                        cote_pari = "(Stat?)"
                    # --- FIN NOUVEAU V26 ---
                    
                    alertes_collectees.append({
                        'Équipe': equipe, 
                        'Statistique': nom_base, 
                        'Record': record,
                        'Série en Cours': en_cours, 
                        '5 Derniers Buts': cinq_derniers_str, 
                        'Prochain Match': prochain_match_str, 
                        'Cote (Pari Inverse)': cote_pari, # <-- NOUVELLE COLONNE
                        'Alerte': alerte_type 
                    })

        # Créer le HTML du tableau d'alertes (MODIFIÉ V26)
        if not alertes_collectees:
            alert_table_html = "<h3 class='no-alerts'>Aucune alerte active pour le moment.</h3>"
        else:
            df_alertes = pd.DataFrame(alertes_collectees)
            df_alertes['Alerte'] = pd.Categorical(df_alertes['Alerte'], categories=["Rouge", "Orange", "Vert"], ordered=True)
            df_alertes = df_alertes.sort_values(by=['Alerte', 'Équipe']).reset_index(drop=True)
            
            # --- MODIFIÉ V26 : S'assurer que la nouvelle colonne est dans le bon ordre
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

        # --- 4. Générer le NOUVEAU tableau de Forme ---
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
        
        # --- 5. Générer le Corps HTML (14 sections cachées) ---
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
                col_record: 'Record',
                col_en_cours: 'Série en Cours',
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

        # --- 6. Définir le Style CSS (MODIFIÉ V26) ---
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
            .main-content {
                display: flex; justify-content: center; align-items: center;
                flex-direction: column; width: 100%; padding-top: 20px; padding-bottom: 20px;
            }
            .section-container.tab-content {
                display: none; width: 90%; 
                max-width: 1000px; /* Augmenté pour la nouvelle colonne */
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
            .styled-table th, .styled-table td { padding: 12px 15px; }
            /* Colonne 1 (Équipe) */
            .styled-table th:nth-child(1), .styled-table td:nth-child(1) { text-align: left; }
            /* Colonnes 2, 3, 4 */
            .styled-table th:nth-child(n+2), .styled-table td:nth-child(n+2) {
                text-align: center; font-weight: bold;
            }
            /* Style pour la colonne 4 (5 Derniers) */
            .styled-table th:nth-child(4), .styled-table td:nth-child(4) {
                font-weight: normal; color: #777; font-size: 0.9em;
            }
            /* Style pour le tableau de forme */
            .form-table th:nth-child(3), .form-table td:nth-child(3) {
                font-weight: normal; color: #777; font-size: 0.9em;
            }
            .form-table th:nth-child(4), .form-table td:nth-child(4) {
                font-weight: normal; color: #17a2b8; font-size: 0.9em;
            }
            
            .styled-table tbody tr {
                border-bottom: 1px solid #dddddd; background-color: #ffffff;
            }
            .styled-table tbody tr:nth-of-type(even) { background-color: #f8f8f8; }
            
            /* --- MODIFIÉ V26 : Règles pour le tableau d'alertes --- */
            .alerts-table td { font-weight: bold !important; }
            .alerts-table td:nth-child(5) { /* 5 Derniers Buts */
                font-weight: normal !important; 
                font-size: 0.9em;
            }
            .alerts-table td:nth-child(6) { /* Prochain Match */
                font-weight: normal !important; 
                color: #17a2b8;
                font-size: 0.9em;
            }
            /* --- NOUVEAU V26 : Style pour la colonne COTE --- */
            .alerts-table td:nth-child(7) { /* Cote (Pari Inverse) */
                font-weight: bold !important; 
                color: #0056b3; /* Bleu foncé */
                font-size: 1.05em;
                text-align: center;
            }
            /* --- FIN MODIFICATION V26 --- */
        </style>
        """

        # --- 7. Le SCRIPT JAVASCRIPT ---
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
        </script>
        """

        # --- 8. Assembler le HTML Final ---
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
            {javascript_code}
        </body>
        </html>
        """

        with open(nom_fichier_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\nSuccès ! Le rapport V27 pour {titre_rapport} a été généré ici : {os.path.abspath(nom_fichier_html)}")

    except Exception as e:
        print(f"\nErreur lors de la génération du fichier HTML : {e}")


# --- (V26) NOUVELLE FONCTION : CHARGER FIXTURES.CSV ---
def charger_fixtures_csv(chemin_fichier_fixtures):
    """
    Charge le fichier fixtures.csv et le transforme en un dictionnaire
    pour une recherche rapide des cotes par équipe.
    """
    print(f"Chargement du fichier de fixtures et cotes : {chemin_fichier_fixtures}")
    if not os.path.exists(chemin_fichier_fixtures):
        print(f"  Avertissement: Fichier '{chemin_fichier_fixtures}' non trouvé.")
        print("  Les cotes et prochains matchs CSV ne seront pas disponibles.")
        return {}
        
    try:
        # Essayer avec latin1 car les CSV de football ont souvent des encodages étranges
        df_fixtures = pd.read_csv(chemin_fichier_fixtures, encoding='latin1')
    except Exception as e:
        print(f"  ERREUR: Impossible de charger {chemin_fichier_fixtures}. {e}")
        print("  Les cotes et prochains matchs CSV ne seront pas disponibles.")
        return {}

    fixtures_dict = {}
    # Identifier toutes les colonnes de cotes présentes dans le CSV
    toutes_colonnes_csv = set(df_fixtures.columns)
    
    # Colonnes de cotes pertinentes (celles de notre MAP + 1X2)
    colonnes_cotes_requises = set(STAT_TO_ODD_COLUMN_MAP.values()) | {'B365H', 'B365D', 'B365A'}
    
    print("  Vérification des colonnes de cotes dans fixtures.csv...")
    colonnes_manquantes = [col for col in STAT_TO_ODD_COLUMN_MAP.values() if col not in toutes_colonnes_csv]
    if colonnes_manquantes:
        print(f"  Avertissement: Les colonnes de cotes suivantes manquent dans fixtures.csv : {colonnes_manquantes}")
        print("  Les cotes correspondantes ne s'afficheront pas.")

    for index, row in df_fixtures.iterrows():
        try:
            home = row['HomeTeam']
            away = row['AwayTeam']
            
            if pd.isna(home) or pd.isna(away):
                continue
            
            # Extraire toutes les cotes disponibles pour ce match
            odds_data = {}
            for col_cote in colonnes_cotes_requises:
                if col_cote in toutes_colonnes_csv and pd.notna(row[col_cote]):
                    try:
                        odds_data[col_cote] = float(row[col_cote])
                    except ValueError:
                        pass # Ignorer si la cote n'est pas un nombre

            # Stocker pour les deux équipes
            # On stocke les cotes même si elles sont vides, 
            # pour la recherche de "Prochain Match"
            fixtures_dict[home] = {'opponent': away, 'loc': 'Home', 'odds': odds_data}
            fixtures_dict[away] = {'opponent': home, 'loc': 'Away', 'odds': odds_data}
        
        except KeyError as ke:
            # Gérer le cas où HomeTeam ou AwayTeam n'existent pas
            print(f"  ERREUR: 'fixtures.csv' doit contenir 'HomeTeam' et 'AwayTeam'.")
            return {} # Arrêter si le format est mauvais
        except Exception as ex:
            print(f"  Avertissement: Erreur lecture ligne fixture: {ex}. Ligne sautée.")

    print(f"  {len(fixtures_dict)} équipes trouvées dans le fichier fixtures.")
    return fixtures_dict

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

# --- Fonction Helper ---
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

# --- Fonction Helper ---
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


# --- FONCTION HELPER (V20) ---
def calculer_score_de_forme(df_equipe, equipe):
    """
    Calcule le score de forme pondéré sur les 5 derniers matchs.
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
        
        # 1. Déterminer V/N/D
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
            
        # 2. Déterminer buts marqués/encaissés
        buts_marques = 0
        buts_encaisses = 0
        if match['HomeTeam'] == equipe:
            buts_marques = match['FTHG']
            buts_encaisses = match['FTAG']
        else:
            buts_marques = match['FTAG']
            buts_encaisses = match['FTHG']
        
        # 3. Bonus
        if buts_marques >= 3:
            score_match += 2 # Bonus Offensif
        if buts_encaisses == 0:
            score_match += 2 # Bonus Défensif (Clean Sheet)
            
        # 4. Appliquer la pondération
        score_pondere = score_match * ponderations[idx]
        scores.append(score_pondere)
        idx += 1
        
        # 5. Créer la chaîne de détails
        details_str.append(f"{resultat_str} ({int(buts_marques)}-{int(buts_encaisses)})")

    total_score = sum(scores)
    # On veut que le plus récent soit à gauche
    details_complets = ", ".join(reversed(details_str))
    
    return total_score, details_complets


# --- FONCTION DE CALCUL V27 (MISE À JOUR) ---
def calculer_tous_les_records_et_series(df, equipes, prochains_matchs_dict_api, fixtures_odds_dict_csv):
    """
    Calcule le RECORD, la SÉRIE EN COURS, les 5 DERNIERS BUTS,
    le SCORE DE FORME, et le PROCHAIN MATCH.
    
    MISE À JOUR V27: Utilise fixtures_odds_dict_csv comme fallback
                     pour le "Prochain Match" si l'API échoue.
    """
    resultats = []
    
    conditions_a_tester = {
        'FT Marque': 'Cond_FT_Score',
        'FT CS': 'Cond_FT_CS',
        'FT No CS': 'Cond_FT_No_CS',
        'FT -0.5': 'Cond_Moins_0_5_FT',
        'FT +1.5': 'Cond_Plus_1_5_FT',
        'FT -1.5': 'Cond_Moins_1_5_FT',
        'FT +2.5': 'Cond_Plus_2_5_FT',
        'FT -2.5': 'Cond_Moins_2_5_FT',
        'FT +3.5': 'Cond_Plus_3_5_FT',
        'FT -3.5': 'Cond_Moins_3_5_FT',
        'FT Nuls': 'Cond_Draw_FT', 
        'MT +0.5': 'Cond_Plus_0_5_HT',
        'MT -0.5': 'Cond_Moins_0_5_HT',
        'MT +1.5': 'Cond_Plus_1_5_HT',
        'MT -1.5': 'Cond_Moins_1_5_HT',
    }
    
    print("Calcul des records, séries, 5 derniers buts et score de forme...")

    for equipe in equipes:
        # On filtre sur TOUTE la base de données
        df_equipe = df[
            (df['HomeTeam'] == equipe) | (df['AwayTeam'] == equipe)
        ].copy()

        if df_equipe.empty:
            continue
            
        record_equipe = {'Équipe': equipe}
        df_equipe = df_equipe.sort_values(by='Date')
        
        # --- Calculer les 5 derniers buts (FT et MT) ---
        if 'TotalGoals' in df_equipe.columns:
            last_5_ft_goals = df_equipe['TotalGoals'].tail(5).astype(int).tolist()
            record_equipe['Last_5_FT_Goals'] = ", ".join(map(str, last_5_ft_goals))
        else:
            record_equipe['Last_5_FT_Goals'] = "N/A"

        if 'TotalHTGoals' in df_equipe.columns:
            last_5_mt_goals = df_equipe['TotalHTGoals'].tail(5).astype(int).tolist()
            record_equipe['Last_5_MT_Goals'] = ", ".join(map(str, last_5_mt_goals))
        else:
            record_equipe['Last_5_MT_Goals'] = "N/A"
            
        # --- Calculer le Score de Forme (V20) ---
        score_forme, details_forme = calculer_score_de_forme(df_equipe, equipe)
        record_equipe['Form_Score'] = score_forme
        record_equipe['Form_Last_5_Str'] = details_forme
        
        # --- (V21) Pré-calcul des stats d'équipe ---
        if 'FTHG' in df_equipe.columns:
            df_equipe['ButsMarques'] = np.where(df_equipe['HomeTeam'] == equipe, df_equipe['FTHG'], df_equipe['FTAG'])
            df_equipe['ButsEncaisses'] = np.where(df_equipe['HomeTeam'] == equipe, df_equipe['FTAG'], df_equipe['FTHG'])
            
            df_equipe['Cond_FT_Score'] = df_equipe['ButsMarques'] > 0
            df_equipe['Cond_FT_CS'] = df_equipe['ButsEncaisses'] == 0
            df_equipe['Cond_FT_No_CS'] = df_equipe['ButsEncaisses'] > 0
            
        # --- (MODIFIÉ V27) Récupérer le prochain match (API d'abord, puis CSV) ---
        
        # 1. Essai de match exact (API)
        prochain = prochains_matchs_dict_api.get(equipe, "N/A") 
        
        if prochain == "N/A":
            # 2. Essai "NomCSV" est dans "NomAPI" (ex: "Man United" in "Manchester United")
            for api_nom, api_match in prochains_matchs_dict_api.items():
                if equipe in api_nom:
                    prochain = api_match
                    break
                    
        if prochain == "N/A":
            # 3. Essai "NomAPI" est dans "NomCSV" (ex: "Wolves" in "Wolverhampton")
            for api_nom, api_match in prochains_matchs_dict_api.items():
                if api_nom in equipe:
                    prochain = api_match
                    break
        
        # --- NOUVEAU V27 : Fallback sur fixtures.csv ---
        if prochain == "N/A":
            match_info_csv = fixtures_odds_dict_csv.get(equipe)
            if match_info_csv:
                opponent = match_info_csv.get('opponent', '?')
                loc = match_info_csv.get('loc', '?')
                loc_str = "Dom" if loc == "Home" else "Ext"
                # On ajoute [CSV] pour savoir d'où vient l'info
                prochain = f"-> {opponent} ({loc_str})"
        # --- FIN NOUVEAU V27 ---
                    
        record_equipe['Prochain_Match'] = prochain
            
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
    """
    Scanne les sous-dossiers (dataYYYY-YYYY) pour trouver
    le plus récent, puis lit les ligues (D1.csv...)
    et leurs équipes.
    Retourne: {'D1': ['Bayern', ...], 'E0': ['Arsenal', ...]}
    """
    ligues_a_analyser = {} # Dictionnaire final
    
    # 1. Trouver tous les dossiers de saison (ex: "data2010-2011", "data2011-2012")
    try:
        dossiers_saison = sorted([
            f for f in glob.glob(f"{dossier_csv_principal}/*") if os.path.isdir(f) and os.path.basename(f).startswith('data')
        ])
        
        if not dossiers_saison:
            print(f"Erreur : Aucun dossier de saison (ex: 'data2010-2011') trouvé dans '{dossier_csv_principal}'")
            return {}
            
        dossier_le_plus_recent = dossiers_saison[-1] # Prend le dernier (ex: data2025-2026)
        print(f"Dossier de la saison la plus récente détecté : {os.path.basename(dossier_le_plus_recent)}")
        
    except Exception as e:
        print(f"Erreur lors de la recherche des dossiers de saison : {e}")
        return {}

    # 2. Scanner ce dossier récent pour trouver les fichiers de ligue (D1.csv, E0.csv...)
    fichiers_ligue = glob.glob(f"{dossier_le_plus_recent}/*.csv")
    if not fichiers_ligue:
        print(f"Erreur : Aucun fichier CSV de ligue trouvé dans '{dossier_le_plus_recent}'")
        return {}

    print(f"\n--- {len(fichiers_ligue)} LIGUES DÉTECTÉES ---")
    
    # 3. Pour chaque fichier (ligue), lire les équipes
    for fichier_path in fichiers_ligue:
        # "D1.csv" -> "D1"
        code_ligue = os.path.basename(fichier_path).replace('.csv', '')
        
        try:
            # Essayer de lire le fichier (avec gestion d'encodage)
            try:
                df_actuel = pd.read_csv(fichier_path)
            except UnicodeDecodeError:
                df_actuel = pd.read_csv(fichier_path, encoding='latin1')
            
            # Lire les équipes
            equipes_domicile = df_actuel['HomeTeam'].dropna().unique()
            equipes_exterieur = df_actuel['AwayTeam'].dropna().unique()
            equipes_actuelles = sorted(list(set(equipes_domicile) | set(equipes_exterieur)))
            
            if equipes_actuelles:
                ligues_a_analyser[code_ligue] = equipes_actuelles
                # Traduire le nom pour l'affichage
                nom_lisible = LEAGUE_NAME_MAPPING.get(code_ligue, f"Code Inconnu: {code_ligue}")
                print(f"  - {code_ligue} -> {nom_lisible} ({len(equipes_actuelles)} équipes trouvées)")
            else:
                print(f"  - Avertissement: {code_ligue} est vide ou ne contient pas d'équipes.")
                
        except Exception as e:
            print(f"  Erreur lors de la lecture du fichier {code_ligue}.csv : {e}")
            
    return ligues_a_analyser

# --- FONCTION API V26 (MISE À JOUR) : CHARGEMENT AVEC PLAGE DE DATES ---
def charger_prochains_matchs_api(api_key, codes_ligues_utilisateur, saison_api):
    """
    Charge les prochains matchs (status=NS) depuis l'API v3.api-football.com
    en utilisant une plage de dates (d'aujourd'hui à la fin de saison).
    
    Retourne un dictionnaire { "NomEquipeAPI": "Description Match", ... }
    """
    prochains_matchs_dict = {}
    headers = { 'x-apisports-key': api_key }
    base_url = "https://v3.api-football.com/fixtures"
    
    date_debut = datetime.date.today().strftime('%Y-%m-%d')
    date_fin = f"{saison_api + 1}-06-15" # Assez large pour couvrir la fin de saison
    
    print(f"\nChargement des prochains matchs via l'API (api-football.com) pour {len(codes_ligues_utilisateur)} (Saison {saison_api})...")
    print(f"Recherche des matchs entre {date_debut} et {date_fin}.")

    for user_code in codes_ligues_utilisateur:
        league_id = LEAGUE_API_MAPPING.get(user_code)
        
        if not league_id:
            print(f"  - Avertissement: Pas de mapping API-Football pour la ligue '{user_code}'. Elle sera sautée.")
            continue

        params = {
            "league": str(league_id),
            "season": str(saison_api),
            "status": "NS", # "Not Started"
            "from": date_debut,
            "to": date_fin
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status() # Lève une exception si le statut est 4xx ou 5xx
            
            data = response.json()
            
            # Gérer les erreurs de l'API (ex: clé invalide, quota)
            errors = data.get('errors')
            if errors:
                print(f"  - ERREUR API pour {user_code} (ID: {league_id}): {errors}")
                continue
                
            matches = data.get('response', [])
            
            if not matches:
                print(f"  - Info: Aucun match programmé ('NS') trouvé pour {user_code} (ID: {league_id}) dans la plage de dates.")
                continue

            matches_tries = sorted(matches, key=lambda x: x['fixture']['date'])
            
            matchs_ajoutes = 0
            for match in matches_tries:
                try:
                    home_team_name = match['teams']['home']['name']
                    away_team_name = match['teams']['away']['name']
                    
                    utc_date = pd.to_datetime(match['fixture']['date'])
                    match_date_str = utc_date.strftime('%d/%m %H:%M') # (Reste en UTC mais formaté)
                    
                    desc_match_domicile = f"{match_date_str} -> {away_team_name} (Dom)"
                    desc_match_exterieur = f"{match_date_str} -> {home_team_name} (Ext)"

                    if home_team_name not in prochains_matchs_dict:
                        prochains_matchs_dict[home_team_name] = desc_match_domicile
                        matchs_ajoutes += 1
                            
                    if away_team_name not in prochains_matchs_dict:
                        prochains_matchs_dict[away_team_name] = desc_match_exterieur
                        
                except Exception as e_match:
                    print(f"  - Erreur lors du parsing d'un match: {e_match}")

            if matchs_ajoutes > 0:
                print(f"  - Succès pour {user_code} (ID: {league_id}). Les prochains matchs ont été trouvés.")

        except requests.exceptions.HTTPError as e_http:
            print(f"  - ERREUR HTTP {e_http.response.status_code} pour {user_code} (ID: {league_id}).")
            print("    Vérifiez votre clé API, votre forfait (quota) ou le code ligue.")
        except requests.exceptions.RequestException as e:
            print(f"  - ERREUR Réseau pour {user_code} (ID: {league_id}): {e}")
        except Exception as e_general:
            print(f"  - ERREUR Inconnue lors du traitement de {user_code}: {e_general}")
            
    print(f"Succès : {len(prochains_matchs_dict)} entrées de prochains matchs chargées depuis l'API (api-football.com).")
    return prochains_matchs_dict
    

# --- FONCTION HUB V15 ---
def creer_page_hub(rapports):
    """
    Crée une page 'index.html' qui sert de portail
    vers tous les rapports de ligue générés.
    """
    nom_fichier = "index.html"
    titre_page = "Hub d'Analyse des Ligues"

    # Trier les rapports par nom de ligue
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
                background-color: #f0f2f5;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                background-color: #ffffff;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                text-align: center;
                max-width: 600px;
                width: 90%;
            }}
            h1 {{
                color: #222;
                margin-top: 0;
            }}
            p {{
                color: #555;
                font-size: 1.1em;
            }}
            ul {{
                list-style-type: none;
                padding: 0;
                margin-top: 30px;
            }}
            li {{
                margin-bottom: 15px;
            }}
            a {{
                display: block;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                padding: 15px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 1.1em;
                transition: background-color 0.3s, transform 0.2s;
            }}
            a:hover {{
                background-color: #0056b3;
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{titre_page}</h1>
            <p>Veuillez sélectionner une ligue à analyser :</p>
            <ul>
                {links_html}
            </ul>
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


# --- POINT D'ENTRÉE DU SCRIPT (MODIFIÉ V27) ---
if __name__ == "__main__":
    
    # !! IMPORTANT !! 
    # Définissez l'année de début de la saison en cours (ex: 2025 pour la saison 2025-2026)
    SAISON_API = 2025 
    
    dossier_csv_principal = "CSV_Data" 
    
    # 1. Trouver TOUS les fichiers CSV dans TOUS les sous-dossiers
    # (On exclut fixtures.csv)
    tous_les_fichiers_csv = []
    for f in glob.glob(f"{dossier_csv_principal}/**/*.csv", recursive=True):
        if os.path.basename(f).lower() != "fixtures.csv":
            tous_les_fichiers_csv.append(f)
    tous_les_fichiers_csv = sorted(tous_les_fichiers_csv)
    
    if not tous_les_fichiers_csv:
        print(f"Erreur : Aucun fichier .csv n'a été trouvé dans les sous-dossiers de '{dossier_csv_principal}'")
        print("Structure attendue : CSV_Data -> data2010-2011 -> D1.csv, E0.csv, ...")
        exit()
            
    # 2. Identifier les ligues et les équipes de la saison la plus récente
    ligues_a_analyser = decouvrir_ligues_et_equipes(dossier_csv_principal)
        
    if not ligues_a_analyser:
        print("Erreur : Aucune ligue ou équipe n'a pu être identifiée.")
        exit()
    
    # 3. Étape 1 : Chargement (tous les fichiers en une fois)
    donnees_completes = charger_donnees(tous_les_fichiers_csv)
    
    # 4. (V26) CHARGER LES FIXTURES ET COTES LOCALES
    chemin_fixtures = os.path.join(dossier_csv_principal, "fixtures.csv")
    fixtures_odds_dict = charger_fixtures_csv(chemin_fixtures)
    
    # 5. (V25) Charger les prochains matchs via l'API (api-football.com)
    if not hasattr(config, 'API_KEY') or "VOTRE_NOUVELLE_CLÉ" in config.API_KEY or config.API_KEY == '':
        print("\n" + "="*50)
        print("  AVERTISSEMENT : Clé API non configurée dans config.py")
        print("  Utilisation de 'fixtures.csv' comme source principale pour les prochains matchs.")
        print("="*50 + "\n")
        prochains_matchs_hub = {}
    else:
        # On passe les codes des ligues (E0, D1...), et la SAISON
        prochains_matchs_hub = charger_prochains_matchs_api(
            config.API_KEY, 
            ligues_a_analyser.keys(),
            SAISON_API 
        )
    
    rapports_generes_pour_hub = []
    
    if donnees_completes is not None:
        
        # 6. Boucle pour traiter CHAQUE ligue
        for code_ligue, equipes_a_analyser in ligues_a_analyser.items():
            
            nom_ligue_lisible = LEAGUE_NAME_MAPPING.get(code_ligue, code_ligue)
            
            print(f"\n--- DÉBUT DU TRAITEMENT : {nom_ligue_lisible} ({code_ligue}) ---")
            print(f"Analyse de {len(equipes_a_analyser)} équipes...")

            # 7. Étape 3 : Calculer tous les records ET séries en cours
            # --- MODIFIÉ V27 : On passe les DEUX dictionnaires de matchs ---
            df_rapport_ligue = calculer_tous_les_records_et_series(
                donnees_completes, 
                equipes_a_analyser, 
                prochains_matchs_hub,   # Dico API
                fixtures_odds_dict      # Dico CSV
            )
            # --- FIN MODIFICATION V27 ---

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
                fixtures_odds_dict 
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