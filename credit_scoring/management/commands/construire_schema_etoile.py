from django.core.management.base import BaseCommand
from credit_scoring.models import (
    get_dossiers_valides, DimTemps, DimNiveauRisque, FaitScoring
)


class Command(BaseCommand):
    help = "Construit le schéma en étoile (dimensions + faits) à partir des dossiers validés"

    def handle(self, *args, **options):
        couleurs = {'Faible': 'vert', 'Modéré': 'orange', 'Élevé': 'rouge'}
        for libelle, couleur in couleurs.items():
            DimNiveauRisque.objects.get_or_create(libelle=libelle, defaults={'couleur': couleur})

        dossiers = get_dossiers_valides()
        compteur = 0

        for d in dossiers:
            date_creation = d.date_creation.date()

            dim_temps, _ = DimTemps.objects.get_or_create(
                date=date_creation,
                defaults={
                    'annee': date_creation.year,
                    'mois': date_creation.month,
                    'jour': date_creation.day,
                    'trimestre': (date_creation.month - 1) // 3 + 1,
                    'nom_mois': date_creation.strftime('%B'),
                },
            )

            dim_niveau = DimNiveauRisque.objects.get(libelle=d.niveau_risque)

            FaitScoring.objects.get_or_create(
                dossier=d,
                defaults={
                    'conseiller': d.conseiller,
                    'temps': dim_temps,
                    'niveau_risque': dim_niveau,
                    'score_risque': d.score_risque,
                    'revenu_mensuel': d.revenu_mensuel,
                    'debt_ratio': d.debt_ratio,
                    'age_client': d.age,
                },
            )
            compteur += 1

        self.stdout.write(self.style.SUCCESS(f"{compteur} faits créés dans le schéma en étoile."))