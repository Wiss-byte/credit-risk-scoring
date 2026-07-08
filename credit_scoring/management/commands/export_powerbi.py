"""
export_powerbi.py
------------------
Commande Django personnalisée qui exporte tous les dossiers crédit
en CSV, prêt à être importé dans Power BI.

Usage : python manage.py export_powerbi
"""

import csv
from django.core.management.base import BaseCommand
from credit_scoring.models import DossierCredit


class Command(BaseCommand):
    help = "Exporte les dossiers crédit en CSV pour Power BI"

    def handle(self, *args, **options):
        chemin_fichier = 'export_dossiers.csv'

        with open(chemin_fichier, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Ligne d'en-tête
            writer.writerow([
                'client_nom', 'client_prenom', 'age', 'revenu_mensuel',
                'revolving_utilization', 'debt_ratio', 'nb_open_credit_lines',
                'nb_real_estate_loans', 'nb_dependents', 'nb_30_59_days_late',
                'nb_60_89_days_late', 'nb_90_days_late', 'score_risque',
                'niveau_risque', 'conseiller', 'date_creation',
            ])

            # Une ligne par dossier en base
            for d in DossierCredit.objects.all():
                writer.writerow([
                    d.client_nom, d.client_prenom, d.age, d.revenu_mensuel,
                    d.revolving_utilization, d.debt_ratio, d.nb_open_credit_lines,
                    d.nb_real_estate_loans, d.nb_dependents, d.nb_30_59_days_late,
                    d.nb_60_89_days_late, d.nb_90_days_late, d.score_risque,
                    d.niveau_risque, d.conseiller.user.username, d.date_creation,
                ])

        self.stdout.write(self.style.SUCCESS(f"{DossierCredit.objects.count()} dossiers exportés dans {chemin_fichier}"))