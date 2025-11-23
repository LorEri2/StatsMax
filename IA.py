import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
import warnings
import os
warnings.filterwarnings('ignore')

class AdvancedFootballPredictor:
    def __init__(self):
        self.model = GradientBoostingClassifier(n_estimators=200, learning_rate=0.1, 
                                                max_depth=5, random_state=42)
        self.label_encoder = LabelEncoder()
        self.team_stats = {}
        
    def load_data(self, filepath):
        """Charge les données depuis un fichier CSV"""
        print("📂 Chargement des données...")
        df = pd.read_csv(filepath)
        
        # Convertir la date
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
        
        # Nettoyer les données
        df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR'])
        df = df.sort_values('Date').reset_index(drop=True)
        
        print(f"✅ {len(df)} matchs chargés")
        print(f"📅 Période: {df['Date'].min().date()} à {df['Date'].max().date()}")
        print(f"🏆 Championnat(s): {df['Div'].unique()}")
        print(f"⚽ Équipes: {df['HomeTeam'].nunique()} équipes différentes")
        
        return df
    
    def calculate_team_form(self, df, team, date, n_matches=5):
        """Calcule la forme récente d'une équipe (points sur les n derniers matchs)"""
        team_matches = df[
            ((df['HomeTeam'] == team) | (df['AwayTeam'] == team)) & 
            (df['Date'] < date)
        ].tail(n_matches)
        
        if len(team_matches) == 0:
            return 0, 0, 0, 0
        
        points = 0
        goals_scored = 0
        goals_conceded = 0
        
        for _, match in team_matches.iterrows():
            if match['HomeTeam'] == team:
                goals_scored += match['FTHG']
                goals_conceded += match['FTAG']
                if match['FTR'] == 'H':
                    points += 3
                elif match['FTR'] == 'D':
                    points += 1
            else:
                goals_scored += match['FTAG']
                goals_conceded += match['FTHG']
                if match['FTR'] == 'A':
                    points += 3
                elif match['FTR'] == 'D':
                    points += 1
        
        return points, goals_scored, goals_conceded, len(team_matches)
    
    def calculate_h2h_stats(self, df, home_team, away_team, date, n_matches=10):
        """Calcule les statistiques des confrontations directes"""
        h2h = df[
            (((df['HomeTeam'] == home_team) & (df['AwayTeam'] == away_team)) |
             ((df['HomeTeam'] == away_team) & (df['AwayTeam'] == home_team))) &
            (df['Date'] < date)
        ].tail(n_matches)
        
        if len(h2h) == 0:
            return 0, 0, 0
        
        home_wins = len(h2h[(h2h['HomeTeam'] == home_team) & (h2h['FTR'] == 'H')])
        home_wins += len(h2h[(h2h['AwayTeam'] == home_team) & (h2h['FTR'] == 'A')])
        
        away_wins = len(h2h[(h2h['HomeTeam'] == away_team) & (h2h['FTR'] == 'H')])
        away_wins += len(h2h[(h2h['AwayTeam'] == away_team) & (h2h['FTR'] == 'A')])
        
        draws = len(h2h[h2h['FTR'] == 'D'])
        
        return home_wins, away_wins, draws
    
    def calculate_home_away_performance(self, df, team, date, is_home=True, n_matches=10):
        """Calcule les performances à domicile ou à l'extérieur"""
        if is_home:
            team_matches = df[(df['HomeTeam'] == team) & (df['Date'] < date)].tail(n_matches)
            if len(team_matches) == 0:
                return 0, 0, 0
            wins = len(team_matches[team_matches['FTR'] == 'H'])
            goals_for = team_matches['FTHG'].mean()
            goals_against = team_matches['FTAG'].mean()
        else:
            team_matches = df[(df['AwayTeam'] == team) & (df['Date'] < date)].tail(n_matches)
            if len(team_matches) == 0:
                return 0, 0, 0
            wins = len(team_matches[team_matches['FTR'] == 'A'])
            goals_for = team_matches['FTAG'].mean()
            goals_against = team_matches['FTHG'].mean()
        
        return wins, goals_for, goals_against
    
    def create_features(self, df):
        """Crée les features pour chaque match"""
        print("\n🔧 Création des features...")
        features = []
        
        for idx, row in df.iterrows():
            if idx % 500 == 0:
                print(f"   Traitement: {idx}/{len(df)} matchs...")
            
            home_team = row['HomeTeam']
            away_team = row['AwayTeam']
            date = row['Date']
            
            # Forme récente
            home_form, home_gf, home_ga, home_matches = self.calculate_team_form(df, home_team, date)
            away_form, away_gf, away_ga, away_matches = self.calculate_team_form(df, away_team, date)
            
            # Confrontations directes
            h2h_home, h2h_away, h2h_draws = self.calculate_h2h_stats(df, home_team, away_team, date)
            
            # Performance domicile/extérieur
            home_wins_h, home_gf_h, home_ga_h = self.calculate_home_away_performance(df, home_team, date, True)
            away_wins_a, away_gf_a, away_ga_a = self.calculate_home_away_performance(df, away_team, date, False)
            
            # Cotes des bookmakers (moyenne pour plus de robustesse)
            odds_home = row.get('B365H', np.nan)
            odds_draw = row.get('B365D', np.nan)
            odds_away = row.get('B365A', np.nan)
            
            # Skip si pas assez d'historique
            if home_matches < 3 or away_matches < 3:
                continue
            
            feature = {
                'home_form': home_form,
                'away_form': away_form,
                'form_diff': home_form - away_form,
                'home_goals_for_avg': home_gf / home_matches if home_matches > 0 else 0,
                'home_goals_against_avg': home_ga / home_matches if home_matches > 0 else 0,
                'away_goals_for_avg': away_gf / away_matches if away_matches > 0 else 0,
                'away_goals_against_avg': away_ga / away_matches if away_matches > 0 else 0,
                'h2h_home_wins': h2h_home,
                'h2h_away_wins': h2h_away,
                'h2h_draws': h2h_draws,
                'home_win_rate_home': home_wins_h / 10,
                'away_win_rate_away': away_wins_a / 10,
                'home_gf_home': home_gf_h,
                'home_ga_home': home_ga_h,
                'away_gf_away': away_gf_a,
                'away_ga_away': away_ga_a,
                'goal_diff': (home_gf - home_ga) - (away_gf - away_ga),
                'odds_home': odds_home if not np.isnan(odds_home) else 2.0,
                'odds_draw': odds_draw if not np.isnan(odds_draw) else 3.0,
                'odds_away': odds_away if not np.isnan(odds_away) else 3.0,
                'odds_favorite': 1 if odds_home < odds_away else 0,
                'result': row['FTR']
            }
            
            features.append(feature)
        
        print(f"✅ {len(features)} features créées")
        return pd.DataFrame(features)
    
    def train(self, feature_df):
        """Entraîne le modèle"""
        print("\n🎯 Entraînement du modèle...")
        
        X = feature_df.drop('result', axis=1)
        y = self.label_encoder.fit_transform(feature_df['result'])
        
        # Split temporel (plus réaliste pour des données temporelles)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Entraînement
        self.model.fit(X_train, y_train)
        
        # Évaluation
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"\n📊 RÉSULTATS:")
        print(f"   Précision sur données d'entraînement: {train_score*100:.2f}%")
        print(f"   Précision sur données de test: {test_score*100:.2f}%")
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=5)
        print(f"   Précision moyenne (CV): {cv_scores.mean()*100:.2f}% (+/- {cv_scores.std()*100:.2f}%)")
        
        # Importance des features
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\n🔍 TOP 10 Features les plus importantes:")
        for idx, row in feature_importance.head(10).iterrows():
            print(f"   {row['feature']:<25} {row['importance']:.4f}")
        
        return X_test, y_test
    
    def predict_match(self, match_data):
        """Prédit le résultat d'un match"""
        X = pd.DataFrame([match_data])
        
        # Prédiction
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        
        result_map = {i: label for i, label in enumerate(self.label_encoder.classes_)}
        predicted_result = result_map[prediction]
        
        result_names = {'H': 'Victoire Domicile', 'D': 'Match Nul', 'A': 'Victoire Extérieur'}
        
        print(f"\n⚽ PRÉDICTION DU MATCH")
        print("=" * 60)
        print(f"Résultat prédit: {result_names[predicted_result]}")
        print(f"\n📈 Probabilités:")
        for label in ['H', 'D', 'A']:
            if label in result_map.values():
                idx = [k for k, v in result_map.items() if v == label][0]
                print(f"   {result_names[label]:<20} {probabilities[idx]*100:>6.2f}%")
        
        return predicted_result, probabilities
    
    def evaluate_predictions(self, X_test, y_test):
        """Évalue les prédictions sur les données de test"""
        predictions = self.model.predict(X_test)
        
        result_map = {i: label for i, label in enumerate(self.label_encoder.classes_)}
        
        # Matrice de confusion
        print("\n📊 ANALYSE DÉTAILLÉE:")
        for actual_idx, actual_label in result_map.items():
            actual_count = sum(y_test == actual_idx)
            if actual_count > 0:
                correct = sum((y_test == actual_idx) & (predictions == actual_idx))
                accuracy = correct / actual_count * 100
                print(f"   {actual_label} - Précision: {accuracy:.1f}% ({correct}/{actual_count})")


# Exemple d'utilisation
if __name__ == "__main__":
    print("🤖 SYSTÈME AVANCÉ DE PRÉDICTION DE MATCHS DE FOOTBALL")
    print("=" * 60)
    
    # Initialiser le prédicteur
    predictor = AdvancedFootballPredictor()
    
    # Charger les données (remplace par ton chemin de fichier)


filepath = r"C:\xampp\htdocs\ScriptMax\CSV_Data\data*\B1.csv"
print(f"Le fichier existe ? {os.path.exists(filepath)}")
print(f"Contenu du dossier CSV_Data:")
for f in os.listdir(r"C:\xampp\htdocs\ScriptMax\CSV_Data"):
    print(f"  - {f}")    
    try:
        df = predictor.load_data(filepath)
        
        # Créer les features
        feature_df = predictor.create_features(df)
        
        # Entraîner le modèle
        X_test, y_test = predictor.train(feature_df)
        
        # Évaluer les prédictions
        predictor.evaluate_predictions(X_test, y_test)
        
        print("\n" + "=" * 60)
        print("✅ MODÈLE ENTRAÎNÉ ET PRÊT À L'EMPLOI!")
        print("\n💡 Pour prédire un nouveau match, utilise:")
        print("   predictor.predict_match(match_data)")
        
    except FileNotFoundError:
        print(f"\n❌ Fichier non trouvé: {filepath}")
        print("   Assure-toi que le chemin est correct et réessaye!")
        print("\n📝 Exemple de structure attendue:")
        print("   - Colonnes obligatoires: Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR")
        print("   - Colonnes optionnelles: B365H, B365D, B365A (cotes)")