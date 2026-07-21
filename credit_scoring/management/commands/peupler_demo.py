"""
peupler_demo.py
----------------
Crée des dossiers de démonstration réalistes pour la soutenance,
avec des profils variés (bons, moyens, mauvais).

Usage : python manage.py peupler_demo
"""

import joblib
import pandas as pd
from pathlib import Path
from django.core.management.base import BaseCommand
from credit_scoring.models import Conseiller, DossierCredit

FEATURE_ORDER = [
    'age', 'revenu_mensuel', 'revolving_utilization', 'debt_ratio',
    'nb_open_credit_lines', 'nb_real_estate_loans', 'nb_dependents',
    'nb_30_59_days_late', 'nb_60_89_days_late', 'nb_90_days_late',
]

PROFILS_DEMO = [
    # (nom, prenom, age, revenu, revolving_util, debt_ratio, nb_credits, nb_immo, nb_charges, retard_30, retard_60, retard_90)
    ("Bennani", "Karim", 34, 12000, 0.15, 0.20, 3, 1, 2, 0, 0, 0),
    ("Alaoui", "Fatima", 45, 18000, 0.10, 0.15, 2, 1, 3, 0, 0, 0),
    ("Tazi", "Youssef", 28, 6500, 0.35, 0.30, 4, 0, 1, 0, 0, 0),
    ("El Idrissi", "Salma", 52, 9000, 0.55, 0.45, 5, 1, 2, 1, 0, 0),
    ("Chraibi", "Omar", 39, 7500, 0.70, 0.55, 6, 0, 3, 1, 1, 0),
    ("Berrada", "Nadia", 26, 4500, 0.85, 0.65, 7, 0, 0, 0, 1, 1),
    ("Fassi", "Hamza", 61, 15000, 0.20, 0.25, 3, 2, 1, 0, 0, 0),
    ("Lahlou", "Amina", 33, 5200, 0.90, 0.70, 8, 0, 2, 1, 1, 1),
]


class Command(BaseCommand):
    help = "Crée des dossiers de démonstration réalistes"

    def handle(self, *args, **options):
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        model = joblib.load(BASE_DIR / 'xgboost_model.pkl')

        conseiller = Conseiller.objects.first()
        if not conseiller:
            self.stdout.write(self.style.ERROR("Aucun conseiller en base. Crée d'abord un compte."))
            return

        for profil in PROFILS_DEMO:
            (nom, prenom, age, revenu, revolving, debt, nb_credits,
             nb_immo, nb_charges, r30, r60, r90) = profil

            donnees = {
                'age': age, 'revenu_mensuel': revenu,
                'revolving_utilization': revolving, 'debt_ratio': debt,
                'nb_open_credit_lines': nb_credits, 'nb_real_estate_loans': nb_immo,
                'nb_dependents': nb_charges, 'nb_30_59_days_late': r30,
                'nb_60_89_days_late': r60, 'nb_90_days_late': r90,
            }

            X = pd.DataFrame([donnees])[FEATURE_ORDER]
            score = round(model.predict_proba(X)[0][1] * 100, 1)
            niveau = "Faible" if score < 30 else "Modéré" if score < 60 else "Élevé"

            DossierCredit.objects.create(
                conseiller=conseiller, client_nom=nom, client_prenom=prenom,
                score_risque=score, niveau_risque=niveau, **donnees,
            )
            self.stdout.write(f"  {nom} {prenom} — score {score}% ({niveau})")

        self.stdout.write(self.style.SUCCESS(f"\n{len(PROFILS_DEMO)} dossiers de démo créés."))