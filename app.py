import pandas as pd
import numpy as np
import glob # Pour lire les fichiers dans un dossier
import os   # Pour gérer les noms de fichiers
import re   # Pour les noms de dossiers
import requests # Pour les requêtes API
import config   # (Bien que nous le contournions pour le test)
import time     # Pour les pauses API (si nécessaire)
import datetime # Pour la V26 API
import streamlit as st # <-- NOUVEAU

# ##########################################################################
# --- 1. DICTIONNAIRES DE CONFIGURATION (Identiques) ---
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
# --- 2. FONCTIONS DE STYLE (Identiques, pour les DataFrames) ---
# ##########################################################################

# Helper 1: Style pour les 13 tableaux de séries (4 colonnes)
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

# Helper 2: Style pour le tableau d'alertes (7 colonnes)
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
    return [style_base, style_base, style_base, style_base, style_5_derniers, style_prochain_match, style_base]

# Helper 3: Style pour le tableau de Forme (4 colonnes)
def colorier_forme_v22(row):
    score = row['Score de Forme']
    style_equipe = ''
    style_score = ''
    style_details = 'font-weight: normal; color: #777; font-size: 0.9em;'
    style_prochain_match = 'font-weight: normal; color: #17a2b8; font-size: 0.9em;'
    if score > 10: 
        style_score = 'color: #2e7d32; font-weight: bold;'
    elif score > 0: 
        style_score = 'color: #28a745;'
    elif score < -5:
        style_score = 'color: #c62828; font-weight: bold;'
    elif score < 0:
        style_score = 'color: #dc3545;'
    return [style_equipe, style_score, style_details, style_prochain_match]


# ##########################################################################
# --- 3. FONCTIONS DE DONNÉES (MISES EN CACHE !) ---
# ##########################################################################

# --- FONCTION DE CHARGEMENT V21 (MISE EN CACHE) ---
@st.cache_data
def charger_donnees(fichiers_csv):
    """
    Charge et combine tous les fichiers CSV.
    Mise en cache par Streamlit.
    """
    all_dfs = []
    # st.write(f"Chargement de {len(fichiers_csv)} fichiers... (Fonction 'charger_donnees' appelée)")
    
    for f in fichiers_csv:
        league_code = os.path.basename(f).replace('.csv', '')
        try:
            df_temp = pd.read_csv(f, on_bad_lines='skip')
            df_temp['LeagueCode'] = league_code 
            all_dfs.append(df_temp)
        except UnicodeDecodeError:
            try:
                df_temp = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
                df_temp['LeagueCode'] = league_code 
                all_dfs.append(df_temp)
            except Exception: pass
        except Exception: pass
            
    if not all_dfs: return None
    df = pd.concat(all_dfs, ignore_index=True)
    
    colonnes_base = ['Date', 'HomeTeam', 'AwayTeam', 'LeagueCode']
    if not all(col in df.columns for col in colonnes_base): return None
    df = df.dropna(subset=colonnes_base) 
    
    # Conversion des dates
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    if df['Date'].isna().all():
        all_dfs_retry = []
        for f in fichiers_csv:
             try:
                 df_temp = pd.read_csv(f, on_bad_lines='skip')
                 df_temp['LeagueCode'] = os.path.basename(f).replace('.csv', '')
                 all_dfs_retry.append(df_temp)
             except: pass
        df = pd.concat(all_dfs_retry, ignore_index=True)
        df = df.dropna(subset=colonnes_base) 
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce') 

    df = df.dropna(subset=['Date']).sort_values(by='Date')
    
    # --- PRÉ-CALCUL DE TOUTES LES CONDITIONS ---
    if 'FTHG' in df.columns and 'FTAG' in df.columns:
        df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce')
        df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce')
        df = df.dropna(subset=['FTHG', 'FTAG'])
        df['TotalGoals'] = df['FTHG'] + df['FTAG']
        df['Cond_Moins_0_5_FT'] = df['TotalGoals'] < 0.5   
        df['Cond_Plus_1_5_FT']  = df['TotalGoals'] > 1.5   
        df['Cond_Moins_1_5_FT'] = df['TotalGoals'] < 1.5   
        df['Cond_Plus_2_5_FT']  = df['TotalGoals'] > 2.5   
        df['Cond_Moins_2_5_FT'] = df['TotalGoals'] < 2.5   
        df['Cond_Plus_3_5_FT']  = df['TotalGoals'] > 3.5   
        df['Cond_Moins_3_5_FT'] = df['TotalGoals'] < 3.5   
    
    if 'HTHG' in df.columns and 'HTAG' in df.columns:
        df['HTHG'] = pd.to_numeric(df['HTHG'], errors='coerce')
        df['HTAG'] = pd.to_numeric(df['HTAG'], errors='coerce')
        df = df.dropna(subset=['HTHG', 'HTAG'])
        df['TotalHTGoals'] = df['HTHG'] + df['HTAG']
        df['Cond_Plus_0_5_HT']  = df['TotalHTGoals'] > 0.5 
        df['Cond_Moins_0_5_HT'] = df['TotalHTGoals'] < 0.5 
        df['Cond_Plus_1_5_HT']  = df['TotalHTGoals'] > 1.5 
        df['Cond_Moins_1_5_HT'] = df['TotalHTGoals'] < 1.5 
        
    if 'FTR' in df.columns:
        df = df.dropna(subset=['FTR'])
        df['Cond_Draw_FT'] = df['FTR'] == 'D' 
    
    print("Données CSV chargées et pré-calculées.")
    return df

# --- FONCTION DE DÉCOUVERTE V17 (MISE EN CACHE) ---
@st.cache_data
def decouvrir_ligues_et_equipes(dossier_csv_principal):
    """
    Scanne les sous-dossiers pour trouver les ligues et équipes
    de la saison la plus récente.
    Mise en cache par Streamlit.
    """
    # st.write("Découverte des ligues... (Fonction 'decouvrir_ligues_et_equipes' appelée)")
    ligues_a_analyser = {}
    try:
        dossiers_saison = sorted([
            f for f in glob.glob(f"{dossier_csv_principal}/*") if os.path.isdir(f) and os.path.basename(f).startswith('data')
        ])
        if not dossiers_saison: return {}
        dossier_le_plus_recent = dossiers_saison[-1] 
    except Exception as e:
        print(f"Erreur recherche dossier saison : {e}")
        return {}

    fichiers_ligue = glob.glob(f"{dossier_le_plus_recent}/*.csv")
    if not fichiers_ligue: return {}

    for fichier_path in fichiers_ligue:
        code_ligue = os.path.basename(fichier_path).replace('.csv', '')
        try:
            try:
                df_actuel = pd.read_csv(fichier_path)
            except UnicodeDecodeError:
                df_actuel = pd.read_csv(fichier_path, encoding='latin1')
            
            equipes_domicile = df_actuel['HomeTeam'].dropna().unique()
            equipes_exterieur = df_actuel['AwayTeam'].dropna().unique()
            equipes_actuelles = sorted(list(set(equipes_domicile) | set(equipes_exterieur)))
            
            if equipes_actuelles:
                # On stocke aussi le nom lisible pour le menu
                nom_lisible = LEAGUE_NAME_MAPPING.get(code_ligue, code_ligue)
                ligues_a_analyser[code_ligue] = {
                    "equipes": equipes_actuelles,
                    "nom_lisible": nom_lisible
                }
        except Exception as e:
            print(f"  Erreur lecture {code_ligue}.csv : {e}")
            
    return ligues_a_analyser

# --- FONCTION API V26 (MISE EN CACHE AVEC TTL) ---
@st.cache_data(ttl=7200) # Cache les résultats pendant 2 heures (7200 secondes)
def charger_prochains_matchs_api(api_key, codes_ligues_utilisateur, saison_api):
    """
    Charge les prochains matchs (status=NS) depuis l'API v3.api-football.com
    en utilisant une plage de dates.
    Mise en cache par Streamlit pour 2 heures.
    """
    # st.write(f"Appel de l'API (api-football.com) pour {len(codes_ligues_utilisateur)} ligues...")
    prochains_matchs_dict = {}
    headers = { 'x-apisports-key': api_key }
    base_url = "https://v3.api-football.com/fixtures"
    
    date_debut = datetime.date.today().strftime('%Y-%m-%d')
    date_fin = f"{saison_api + 1}-06-15" 

    for user_code in codes_ligues_utilisateur:
        league_id = LEAGUE_API_MAPPING.get(user_code)
        if not league_id:
            continue

        params = {
            "league": str(league_id),
            "season": str(saison_api),
            "status": "NS",
            "from": date_debut,
            "to": date_fin
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status() 
            data = response.json()
            if data.get('errors'):
                print(f"  - ERREUR API pour {user_code}: {data.get('errors')}")
                continue
                
            matches = data.get('response', [])
            if not matches:
                continue

            matches_tries = sorted(matches, key=lambda x: x['fixture']['date'])
            
            for match in matches_tries:
                try:
                    home_team_name = match['teams']['home']['name']
                    away_team_name = match['teams']['away']['name']
                    utc_date = pd.to_datetime(match['fixture']['date'])
                    match_date_str = utc_date.strftime('%d/%m %H:%M')
                    
                    desc_match_domicile = f"{match_date_str} -> {away_team_name} (Dom)"
                    desc_match_exterieur = f"{match_date_str} -> {home_team_name} (Ext)"

                    if home_team_name not in prochains_matchs_dict:
                        prochains_matchs_dict[home_team_name] = desc_match_domicile
                    if away_team_name not in prochains_matchs_dict:
                        prochains_matchs_dict[away_team_name] = desc_match_exterieur
                except Exception: pass
        except Exception as e:
            print(f"  - ERREUR Inconnue lors du traitement de {user_code}: {e}")
            
    print(f"Succès : {len(prochains_matchs_dict)} entrées de prochains matchs chargées depuis l'API (api-football.com).")
    return prochains_matchs_dict


# --- Fonctions de Calcul des Séries (Identiques) ---

def trouver_max_serie_pour_colonne(df_equipe, nom_colonne_condition):
    if nom_colonne_condition not in df_equipe.columns:
        return 0 
    df_equipe = df_equipe.sort_values(by='Date')
    df_equipe['streak_group'] = (df_equipe[nom_colonne_condition] != df_equipe[nom_colonne_condition].shift()).cumsum()
    streaks_when_true = df_equipe[df_equipe[nom_colonne_condition] == True]
    if streaks_when_true.empty:
        max_streak = 0
    else:
        max_streak = int(streaks_when_true.groupby('streak_group').size().max())
    return max_streak

def trouver_serie_en_cours_pour_colonne(df_equipe, nom_colonne_condition):
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

def calculer_score_de_forme(df_equipe, equipe):
    if 'FTR' not in df_equipe.columns or 'FTHG' not in df_equipe.columns:
        return 0, "N/A"
    df_equipe = df_equipe.sort_values(by='Date')
    last_5_games = df_equipe.tail(5)
    if len(last_5_games) < 5:
        return 0, "Pas assez de matchs"
    scores, details_str = [], []
    ponderations = [0.2, 0.4, 0.6, 0.8, 1.0]
    idx = 0
    for i, (index, match) in enumerate(last_5_games.iterrows()):
        score_match = 0
        resultat = match['FTR']
        if (match['HomeTeam'] == equipe and resultat == 'H') or (match['AwayTeam'] == equipe and resultat == 'A'):
            score_match += 5; resultat_str = "V"
        elif resultat == 'D':
            score_match += 1; resultat_str = "N"
        else:
            score_match -= 3; resultat_str = "D"
            
        buts_marques = match['FTHG'] if match['HomeTeam'] == equipe else match['FTAG']
        buts_encaisses = match['FTAG'] if match['HomeTeam'] == equipe else match['FTHG']
        
        if buts_marques >= 3: score_match += 2
        if buts_encaisses == 0: score_match += 2
            
        scores.append(score_match * ponderations[idx])
        idx += 1
        details_str.append(f"{resultat_str} ({int(buts_marques)}-{int(buts_encaisses)})")
    
    return sum(scores), ", ".join(reversed(details_str))

# --- FONCTION DE CALCUL V25 (MISE À JOUR & MISE EN CACHE) ---
#
# CORRECTION 1: Ajouter un underscore à _prochains_matchs_dict
# pour dire à Streamlit de ne pas essayer de le "hasher".
#
@st.cache_data
def calculer_tous_les_records_et_series(df, equipes, _prochains_matchs_dict):
    """
    Calcule toutes les stats pour une liste d'équipes donnée.
    Mise en cache par Streamlit.
    """
    # st.write(f"Calcul des records pour {len(equipes)} équipes... (Fonction 'calculer_tous_les_records_et_series' appelée)")
    resultats = []
    
    conditions_a_tester = {
        'FT Marque': 'Cond_FT_Score', 'FT CS': 'Cond_FT_CS', 'FT No CS': 'Cond_FT_No_CS',
        'FT -0.5': 'Cond_Moins_0_5_FT', 'FT +1.5': 'Cond_Plus_1_5_FT', 'FT -1.5': 'Cond_Moins_1_5_FT',
        'FT +2.5': 'Cond_Plus_2_5_FT', 'FT -2.5': 'Cond_Moins_2_5_FT', 'FT +3.5': 'Cond_Plus_3_5_FT',
        'FT -3.5': 'Cond_Moins_3_5_FT', 'FT Nuls': 'Cond_Draw_FT', 
        'MT +0.5': 'Cond_Plus_0_5_HT', 'MT -0.5': 'Cond_Moins_0_5_HT',
        'MT +1.5': 'Cond_Plus_1_5_HT', 'MT -1.5': 'Cond_Moins_1_5_HT',
    }
    
    for equipe in equipes:
        df_equipe = df[(df['HomeTeam'] == equipe) | (df['AwayTeam'] == equipe)].copy()
        if df_equipe.empty: continue
            
        record_equipe = {'Équipe': equipe}
        df_equipe = df_equipe.sort_values(by='Date')
        
        if 'TotalGoals' in df_equipe.columns:
            record_equipe['Last_5_FT_Goals'] = ", ".join(map(str, df_equipe['TotalGoals'].tail(5).astype(int).tolist()))
        else: record_equipe['Last_5_FT_Goals'] = "N/A"
        if 'TotalHTGoals' in df_equipe.columns:
            record_equipe['Last_5_MT_Goals'] = ", ".join(map(str, df_equipe['TotalHTGoals'].tail(5).astype(int).tolist()))
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
            
        # --- (V25) Récupérer le prochain match (logique de matching flou) ---
        # CORRECTION 1 (suite) : Utiliser la variable avec underscore
        prochain = _prochains_matchs_dict.get(equipe, "N/A") # 1. Essai de match exact
        if prochain == "N/A":
            for api_nom, api_match in _prochains_matchs_dict.items(): # 2. Essai "NomCSV" in "NomAPI"
                if equipe in api_nom:
                    prochain = api_match; break
        if prochain == "N/A":
            for api_nom, api_match in _prochains_matchs_dict.items(): # 3. Essai "NomAPI" in "NomCSV"
                if api_nom in equipe:
                    prochain = api_match; break
        record_equipe['Prochain_Match'] = prochain
            
        for nom_base, nom_col_data in conditions_a_tester.items():
            record_equipe[f'{nom_base}_Record'] = trouver_max_serie_pour_colonne(df_equipe, nom_col_data)
            record_equipe[f'{nom_base}_EnCours'] = trouver_serie_en_cours_pour_colonne(df_equipe, nom_col_data)
            
        resultats.append(record_equipe)

    return pd.DataFrame(resultats).sort_values(by='Équipe').reset_index(drop=True)


# ##########################################################################
# --- 4. APPLICATION STREAMLIT (POINT D'ENTRÉE) ---
# ##########################################################################

def main():
    
    # --- Configuration de la page ---
    st.set_page_config(
        page_title="Analyse de Séries de Matchs",
        page_icon="⚽",
        layout="wide" # "centered" ou "wide"
    )

    # --- CSS Personnalisé pour Streamlit ---
    # On cache les éléments inutiles et on ajuste les tables
    st.markdown("""
        <style>
            header {visibility: hidden;}
            footer {visibility: hidden;}
            #MainMenu {visibility: hidden;}
            .block-container { padding-top: 1rem; }
            .stDataFrame { 
                border: 0; 
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); 
                border-radius: 8px;
            }
            .stDataFrame th {
                background-color: #333;
                color: white;
                font-weight: bold;
            }
            /* Style pour les onglets */
            [data-baseweb="tab-list"] {
                gap: 8px;
            }
            [data-baseweb="tab"] {
                background-color: #f0f2f5;
                border-radius: 8px 8px 0 0;
                padding: 10px 16px;
                font-weight: 600;
            }
            [data-baseweb="tab"][aria-selected="true"] {
                background-color: #007bff;
                color: white;
            }
        </style>
    """, unsafe_allow_html=True)


    # --- Constantes ---
    SAISON_API = 2025 # Année de début de saison (ex: 2025 pour 2025-2026)
    DOSSIER_CSV = "CSV_Data" 

    # --- 1. CHARGEMENT DES DONNÉES (MIS EN CACHE) ---
    # st.write("Début du chargement...")
    
    # CORRECTION : Clé API mise "en dur" pour le test
    api_key = "3f945179c98e632e40a88be42d7cd9f2"  # <-- COLLEZ VOTRE CLÉ ICI
    
    # Vérification simple
    if not api_key or "VOTRE_VRAIE_CLÉ_API_ICI" in api_key:
        st.error("ERREUR : Veuillez coller votre clé API directement dans le script 'app.py'.")
        return
    
    # Trouver tous les fichiers CSV
    tous_les_fichiers_csv = sorted(glob.glob(f"{DOSSIER_CSV}/**/*.csv", recursive=True))
    if not tous_les_fichiers_csv:
        st.error(f"Aucun fichier .csv trouvé dans '{DOSSIER_CSV}'.")
        return

    # Charger les données CSV historiques
    donnees_completes = charger_donnees(tous_les_fichiers_csv)
    if donnees_completes is None:
        st.error("Échec du chargement des données CSV.")
        return

    # Découvrir les ligues et équipes de la saison récente
    ligues_a_analyser = decouvrir_ligues_et_equipes(DOSSIER_CSV)
    if not ligues_a_analyser:
        st.error("Aucune ligue ou équipe n'a pu être identifiée depuis les CSV récents.")
        return

    # Charger les prochains matchs (cache de 2h)
    #
    # CORRECTION 2: Convertir .keys() en tuple()
    #
    prochains_matchs_hub = charger_prochains_matchs_api(
        api_key, 
        tuple(ligues_a_analyser.keys()),
        SAISON_API
    )
    # st.write("Toutes les données sont chargées.")

    # --- 2. BARRE LATÉRALE DE NAVIGATION ---
    
    st.sidebar.title("Hub d'Analyse ⚽")
    st.sidebar.write("Veuillez sélectionner une ligue à analyser.")

    # Créer une liste triée des noms de ligues pour le menu
    liste_ligues_menu = sorted(
        [(data['nom_lisible'], code) for code, data in ligues_a_analyser.items()]
    )
    
    # Transformer en une liste de noms lisibles pour le selectbox
    noms_lisibles_menu = [nom for nom, code in liste_ligues_menu]
    
    # Selectbox dans la sidebar
    nom_ligue_choisie = st.sidebar.selectbox(
        "Ligues Disponibles",
        noms_lisibles_menu,
        index=0 # Sélectionne la première par défaut
    )
    
    # Trouver le code_ligue et les équipes correspondant au nom choisi
    code_ligue_choisi = None
    for nom, code in liste_ligues_menu:
        if nom == nom_ligue_choisie:
            code_ligue_choisi = code
            break
            
    if code_ligue_choisi is None:
        st.error("Erreur de sélection de ligue.")
        return
        
    equipes_a_analyser = ligues_a_analyser[code_ligue_choisi]['equipes']


    # --- 3. CALCUL DU RAPPORT POUR LA LIGUE CHOISIE ---
    
    # Cette fonction est mise en cache, donc c'est instantané si on change
    # de ligue puis qu'on y revient.
    df_rapport_ligue = calculer_tous_les_records_et_series(
        donnees_completes, 
        tuple(equipes_a_analyser), # tuple() est requis pour le cache
        prochains_matchs_hub
    )

    if df_rapport_ligue.empty:
        st.warning("Aucune donnée de rapport n'a pu être calculée pour cette ligue.")
        return

    # --- 4. GÉNÉRATION DES DONNÉES D'AFFICHAGE ---

    # --- Onglet Forme ---
    cols_forme = ['Équipe', 'Form_Score', 'Form_Last_5_Str', 'Prochain_Match']
    if 'Form_Score' in df_rapport_ligue.columns:
        df_forme = df_rapport_ligue[cols_forme].copy()
        df_forme = df_forme.rename(columns={
            'Form_Score': 'Score de Forme',
            'Form_Last_5_Str': '5 Derniers (Détails)',
            'Prochain_Match': 'Prochain Match'
        })
        df_forme = df_forme.sort_values(by='Score de Forme', ascending=False)
        
        # Appliquer le style
        styler_forme = df_forme.style.apply(colorier_forme_v22, axis=1) \
                                     .format({'Score de Forme': '{:+.1f}'}) \
                                     .hide(axis="index")
    else:
        styler_forme = pd.DataFrame(columns=["Info"]).style.hide() # Vide

    # --- Onglet Alertes ---
    stats_a_afficher = {
        'FT Marque': ['ft_marque', 'Record - L\'équipe Marque (FT)'], 'FT CS': ['ft_cs', 'Record - Clean Sheet (FT)'],
        'FT No CS': ['ft_no_cs', 'Record - Non Clean Sheet (FT)'], 'FT -0.5': ['ft_moins_0_5', 'Record - Fin de Match -0.5 (0 Buts)'],
        'FT +1.5': ['ft_plus_1_5', 'Record - Fin de Match +1.5 (2+ Buts)'], 'FT -1.5': ['ft_moins_1_5', 'Record - Fin de Match -1.5 (0-1 Buts)'],
        'FT +2.5': ['ft_plus_2_5', 'Record - Fin de Match +2.5 (3+ Buts)'], 'FT -2.5': ['ft_moins_2_5', 'Record - Fin de Match -2.5 (0-2 Buts)'],
        'FT +3.5': ['ft_plus_3_5', 'Record - Fin de Match +3.5 (4+ Buts)'], 'FT -3.5': ['ft_moins_3_5', 'Record - Fin de Match -3.5 (0-3 Buts)'],
        'FT Nuls': ['ft_nuls', 'Record - Fin de Match (Nuls)'], 'MT +0.5': ['mt_plus_0_5', 'Record - Mi-Temps +0.5 (1+ Buts MT)'],
        'MT -0.5': ['mt_moins_0_5', 'Record - Mi-Temps -0.5 (0 Buts MT)'], 'MT +1.5': ['mt_plus_1_5', 'Record - Mi-Temps +1.5 (2+ Buts MT)'],
        'MT -1.5': ['mt_moins_1_5', 'Record - Mi-Temps -1.5 (0-1 Buts MT)'],
    }
    
    alertes_collectees = []
    for nom_base, config in stats_a_afficher.items():
        col_record = f'{nom_base}_Record'
        col_en_cours = f'{nom_base}_EnCours'
        if col_record not in df_rapport_ligue.columns: continue
        
        col_5_derniers = 'Last_5_FT_Goals' if nom_base.startswith('FT') else 'Last_5_MT_Goals'
        
        for index, row in df_rapport_ligue.iterrows():
            record = row[col_record]
            en_cours = row[col_en_cours]
            alerte_type = None
            if en_cours > 0 and en_cours == record: alerte_type = 'Rouge'
            elif en_cours > 0 and en_cours == record - 1: alerte_type = 'Orange'
            elif en_cours > 0 and en_cours == record - 2: alerte_type = 'Vert'
            
            if alerte_type:
                alertes_collectees.append({
                    'Équipe': row['Équipe'], 'Statistique': nom_base, 'Record': record,
                    'Série en Cours': en_cours, 
                    '5 Derniers Buts': row.get(col_5_derniers, "N/A"), 
                    'Prochain Match': row.get('Prochain_Match', "N/A"),
                    'Alerte': alerte_type 
                })

    if alertes_collectees:
        df_alertes = pd.DataFrame(alertes_collectees)
        df_alertes['Alerte'] = pd.Categorical(df_alertes['Alerte'], categories=["Rouge", "Orange", "Vert"], ordered=True)
        df_alertes = df_alertes.sort_values(by=['Alerte', 'Équipe'])
        styler_alertes = df_alertes.style.apply(colorier_tableau_alertes_v22, axis=1) \
                                         .hide(axis="index") \
                                         .hide(['Alerte'], axis=1)
    else:
        styler_alertes = None # Sera géré plus bas

    # --- 5. AFFICHAGE DE LA PAGE PRINCIPALE ---
    
    st.title(f"📈 {nom_ligue_choisie}")
    
    # --- Créer les onglets ---
    noms_onglets_stats = list(stats_a_afficher.keys())
    
    # Créer la liste des onglets pour st.tabs
    # ['📈 Forme', '⚠️ Alertes', 'FT Marque', 'FT CS', ...]
    onglets_tabs = st.tabs(["📈 Forme", "⚠️ Alertes"] + noms_onglets_stats)

    # --- Onglet 1: Forme ---
    with onglets_tabs[0]:
        st.subheader("État de Forme Actuel")
        st.dataframe(styler_forme, use_container_width=True)

    # --- Onglet 2: Alertes ---
    with onglets_tabs[1]:
        st.subheader("Tableau des Alertes (Toutes Séries)")
        if styler_alertes:
            st.dataframe(styler_alertes, use_container_width=True)
        else:
            st.info("Aucune alerte active (Rouge, Orange ou Verte) pour cette ligue.")

    # --- Onglets 3 à 17: Toutes les autres stats ---
    for i, (nom_base, config) in enumerate(stats_a_afficher.items()):
        
        with onglets_tabs[i + 2]: # On commence à l'index 2
            
            titre_section = config[1]
            col_record = f'{nom_base}_Record'
            col_en_cours = f'{nom_base}_EnCours'
            col_5_derniers = 'Last_5_FT_Goals' if nom_base.startswith('FT') else 'Last_5_MT_Goals'
            nom_col_5_derniers = '5 Derniers (FT)' if nom_base.startswith('FT') else '5 Derniers (MT)'
            
            st.subheader(titre_section)
            
            if col_record not in df_rapport_ligue.columns:
                st.warning(f"Données non disponibles pour '{nom_base}'.")
                continue
            
            df_stat = df_rapport_ligue[['Équipe', col_record, col_en_cours, col_5_derniers]].copy()
            df_stat = df_stat.rename(columns={
                col_record: 'Record',
                col_en_cours: 'Série en Cours',
                col_5_derniers: nom_col_5_derniers
            })
            df_stat = df_stat.sort_values(by='Record', ascending=False)
            
            styler_stat = df_stat.style.apply(colorier_series_v19, axis=1) \
                                       .hide(axis="index")
            
            st.dataframe(styler_stat, use_container_width=True)


# --- Point d'entrée du Script ---
if __name__ == "__main__":
    main()