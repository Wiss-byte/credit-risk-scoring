"""
train_model.py
--------------
Entraîne un modèle XGBoost de scoring de crédit sur le dataset EQDOM
synthétique, l'évalue, puis le sauvegarde pour l'utiliser dans Django.
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
from xgboost import XGBClassifier
import joblib

# --- 1. CHARGER LE DATASET ---
df = pd.read_csv('ml/eqdom_dataset.csv')

# Features = toutes les colonnes SAUF la target
X = df.drop(columns=['SeriousDlqin2yrs'])
# Target = ce qu'on veut prédire
y = df['SeriousDlqin2yrs']

print(f"Nombre de features : {X.shape[1]}")
print(f"Colonnes : {list(X.columns)}")

# --- 2. SPLIT TRAIN / TEST ---
# test_size=0.2 → 20% des données réservées au test
# random_state=42 → reproductibilité (comme le seed précédent)
# stratify=y → garde la même proportion de défauts dans train ET test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTrain : {len(X_train)} clients")
print(f"Test  : {len(X_test)} clients")

# --- 3. ENTRAÎNEMENT DU MODÈLE ---

# On calcule le déséquilibre réel du train set (pas du dataset entier,
# pour être cohérent avec ce que le modèle voit vraiment)
ratio = (y_train == 0).sum() / (y_train == 1).sum()
print(f"\nRatio de déséquilibre (scale_pos_weight) : {ratio:.2f}")

model = XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.1,
    eval_metric='logloss',
    scale_pos_weight=ratio,   # <-- pénalise plus les erreurs sur les défauts
    random_state=42
)

model.fit(X_train, y_train)
print("\n✅ Modèle entraîné.")

# --- 4. ÉVALUATION SUR LE TEST SET (données jamais vues) ---
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]  # probabilité de défaut

auc = roc_auc_score(y_test, y_proba)
print(f"\nAUC (qualité du modèle, 0.5=hasard, 1.0=parfait) : {auc:.3f}")
print("\nRapport détaillé :")
print(classification_report(y_test, y_pred))

# --- 5. IMPORTANCE DES VARIABLES (quelles features comptent le plus) ---
importances = pd.Series(model.feature_importances_, index=X.columns)
print("\nImportance des variables :")
print(importances.sort_values(ascending=False))

# --- 6. SAUVEGARDE DU MODÈLE ---
joblib.dump(model, 'xgboost_model.pkl')
print("\n💾 Modèle sauvegardé dans xgboost_model.pkl")
# --- 7. COURBE PRECISION-RECALL : choisir le meilleur seuil ---
from sklearn.metrics import precision_recall_curve

precisions, recalls, seuils = precision_recall_curve(y_test, y_proba)

# On cherche le seuil qui donne le meilleur compromis (F1-score max)
f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-9)
meilleur_index = f1_scores.argmax()
meilleur_seuil = seuils[meilleur_index]

print(f"\n📊 Seuil par défaut (0.5) vs seuil optimal ({meilleur_seuil:.2f}) :")
print(f"   À 0.5        → precision={precisions[np.searchsorted(seuils, 0.5)]:.2f}")
print(f"   Seuil optimal → precision={precisions[meilleur_index]:.2f}, recall={recalls[meilleur_index]:.2f}, F1={f1_scores[meilleur_index]:.2f}")

# On sauvegarde le seuil optimal pour l'utiliser dans Django plus tard
import json
with open('ml/seuil_optimal.json', 'w') as f:
    json.dump({'seuil': float(meilleur_seuil)}, f)
    # --- 8. RECHERCHE DES MEILLEURS HYPERPARAMÈTRES ---
from sklearn.model_selection import GridSearchCV

param_grid = {
    'max_depth': [3, 4, 5, 6],
    'n_estimators': [100, 200, 300],
    'learning_rate': [0.05, 0.1, 0.2],
}

print("\n🔍 Recherche des meilleurs hyperparamètres (patiente, ça prend 1-2 min)...")

grid_search = GridSearchCV(
    estimator=XGBClassifier(
        eval_metric='logloss',
        scale_pos_weight=ratio,
        random_state=42
    ),
    param_grid=param_grid,
    scoring='f1',       # on optimise le F1 de la classe défaut, pas l'accuracy
    cv=5,                # 5 tranches de cross-validation
    n_jobs=-1             # utilise tous les cœurs du CPU en parallèle
)

grid_search.fit(X_train, y_train)

print(f"\n✅ Meilleurs paramètres trouvés : {grid_search.best_params_}")
print(f"   Meilleur F1 en cross-validation : {grid_search.best_score_:.3f}")

# On récupère le meilleur modèle trouvé
best_model = grid_search.best_estimator_

# On le réévalue sur le test set (données jamais vues)
y_pred_best = best_model.predict(X_test)
print("\nRapport avec le modèle optimisé :")
print(classification_report(y_test, y_pred_best))

# On sauvegarde CE modèle à la place de l'ancien
joblib.dump(best_model, 'xgboost_model.pkl')
print("\n💾 Modèle optimisé sauvegardé (écrase l'ancien)")