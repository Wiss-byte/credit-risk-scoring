"""
calculer_stats_gold.py
------------------------
Calcule les statistiques mensuelles (couche Gold) à partir des
dossiers validés (couche Silver), et les stocke pour un accès rapide.

Usage : python manage.py calculer_stats_gold
"""

from django.core.management.base import BaseCommand
from django.db.models.functions import TruncMonth
from django.db.models import Count, Avg
from credit_scoring.models import get_dossiers_valides, StatsMensuelles


class Command(BaseCommand):
    help = "Calcule les stats mensuelles (couche Gold) à partir des dossiers validés (Silver)"

    def handle(self, *args, **options):
        dossiers_valides = get_dossiers_valides()

        # Groupe par mois (TruncMonth) et calcule les agrégats
        stats_par_mois = (
            dossiers_valides
            .annotate(mois=TruncMonth('date_creation'))
            .values('mois')
            .annotate(
                nb_dossiers=Count('id'),
                score_moyen=Avg('score_risque'),
            )
        )

        for stat in stats_par_mois:
            nb_faible = dossiers_valides.filter(
                date_creation__year=stat['mois'].year,
                date_creation__month=stat['mois'].month,
                niveau_risque='Faible',
            ).count()
            nb_modere = dossiers_valides.filter(
                date_creation__year=stat['mois'].year,
                date_creation__month=stat['mois'].month,
                niveau_risque='Modéré',
            ).count()
            nb_eleve = dossiers_valides.filter(
                date_creation__year=stat['mois'].year,
                date_creation__month=stat['mois'].month,
                niveau_risque='Élevé',
            ).count()

            StatsMensuelles.objects.update_or_create(
                mois=stat['mois'].date(),
                defaults={
                    'nb_dossiers': stat['nb_dossiers'],
                    'score_moyen': round(stat['score_moyen'], 1),
                    'nb_faible': nb_faible,
                    'nb_modere': nb_modere,
                    'nb_eleve': nb_eleve,
                },
            )
            self.stdout.write(f"  {stat['mois'].strftime('%Y-%m')} : {stat['nb_dossiers']} dossiers, score moyen {stat['score_moyen']:.1f}%")

        self.stdout.write(self.style.SUCCESS(f"\n{len(stats_par_mois)} mois calculés (couche Gold)."))