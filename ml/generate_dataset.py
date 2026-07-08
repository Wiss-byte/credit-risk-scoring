"""
generate_dataset.py
--------------------
Génère un dataset synthétique de clients EQDOM (crédit à la consommation
au Maroc) pour entraîner un modèle de scoring de risque de crédit.

Concept clé : on simule des clients réalistes, puis on calcule leur
probabilité de défaut avec une formule logique (pas au hasard), pour
que le modèle ML ait un vrai pattern à apprendre.
"""

import numpy as np
import pandas as pd

# On fixe une "graine" aléatoire : ça rend les résultats reproductibles.
# Si tu relances le script, tu obtiens EXACTEMENT le même dataset.
np.random.seed(42)

N = 20000  # nombre de clients simulés

# --- 1. GÉNÉRATION DES FEATURES (variables explicatives) ---

# Âge : entre 20 et 65 ans, distribution centrée autour de 38 ans
age = np.random.normal(loc=38, scale=10, size=N).clip(20, 65).astype(int)

# Revenu mensuel en MAD : distribution asymétrique (beaucoup de gens
# autour du revenu médian marocain, quelques hauts revenus)
revenu_mensuel = np.random.lognormal(mean=8.2, sigma=0.45, size=N).clip(2500, 40000)

# Taux d'utilisation du crédit renouvelable : entre 0 et 1
# (0 = n'utilise pas son découvert/carte, 1 = utilise sa limite max)
revolving_utilization = np.random.beta(a=2, b=5, size=N)

# Ratio d'endettement (dettes mensuelles / revenu mensuel)
debt_ratio = np.random.beta(a=2, b=4, size=N)

# Nombre de lignes de crédit ouvertes (cartes, prêts en cours...)
nb_open_credit_lines = np.random.poisson(lam=4, size=N).clip(0, 15)

# Nombre de prêts immobiliers en cours
nb_real_estate_loans = np.random.poisson(lam=0.4, size=N).clip(0, 3)

# Nombre de personnes à charge
nb_dependents = np.random.poisson(lam=1.5, size=N).clip(0, 6)

# Retards de paiement passés (30-59 jours, 60-89 jours, 90+ jours)
# On simule que la plupart des gens n'ont jamais eu de retard
nb_30_59_days_late = np.random.poisson(lam=0.3, size=N).clip(0, 10)
nb_60_89_days_late = np.random.poisson(lam=0.15, size=N).clip(0, 10)
nb_90_days_late = np.random.poisson(lam=0.1, size=N).clip(0, 10)

# --- 2. CALCUL DE LA PROBABILITÉ DE DÉFAUT (la logique métier) ---
# On combine les variables avec des poids, comme le ferait un analyste
# crédit. Plus le score est élevé, plus le risque de défaut est grand.

risk_score = (
    - 0.04 * (revenu_mensuel / 1000)      # revenu élevé → risque baisse
    + 3.5  * debt_ratio                    # endettement élevé → risque monte
    + 2.5  * revolving_utilization         # utilise déjà tout son crédit → risque monte
    + 0.8  * nb_30_59_days_late            # retards passés → mauvais signe
    + 1.5  * nb_60_89_days_late
    + 2.5  * nb_90_days_late
    + 0.15 * nb_dependents                 # charges familiales → légère hausse
    - 0.02 * age                           # plus âgé → légèrement plus stable
    + np.random.normal(0, 1.2, size=N)     # bruit aléatoire (réalisme)
)

# On transforme ce score en probabilité entre 0 et 1 avec une fonction
# sigmoïde (classique en scoring de crédit / régression logistique)
proba_defaut = 1 / (1 + np.exp(-risk_score + 4.5))

# La target finale : 1 si défaut, 0 sinon, tirée aléatoirement selon
# cette probabilité (comme la réalité : même un profil "à risque" ne
# fait pas TOUJOURS défaut)
serious_dlqin2yrs = np.random.binomial(1, proba_defaut)

# --- 3. ASSEMBLAGE DU DATASET FINAL ---
df = pd.DataFrame({
    'age': age,
    'revenu_mensuel': revenu_mensuel.round(0),
    'revolving_utilization': revolving_utilization.round(3),
    'debt_ratio': debt_ratio.round(3),
    'nb_open_credit_lines': nb_open_credit_lines,
    'nb_real_estate_loans': nb_real_estate_loans,
    'nb_dependents': nb_dependents,
    'nb_30_59_days_late': nb_30_59_days_late,
    'nb_60_89_days_late': nb_60_89_days_late,
    'nb_90_days_late': nb_90_days_late,
    'SeriousDlqin2yrs': serious_dlqin2yrs,   # <-- la target
})

df.to_csv('ml/eqdom_dataset.csv', index=False)

print(f"Dataset généré : {len(df)} clients")
print(f"Taux de défaut global : {df['SeriousDlqin2yrs'].mean():.1%}")
print(df.head())