from django.db import models
from django.contrib.auth.models import User


class Conseiller(models.Model):
    ROLES = [
        ('conseiller', 'Conseiller'),
        ('admin', 'Administrateur'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    agence = models.CharField(max_length=100, default="Agence Casablanca Centre")
    role = models.CharField(max_length=20, choices=ROLES, default='conseiller')

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.agence} ({self.role})"


class DossierCredit(models.Model):
    # ForeignKey : plusieurs dossiers peuvent appartenir au même conseiller
    conseiller = models.ForeignKey(Conseiller, on_delete=models.CASCADE, related_name='dossiers')

    client_nom = models.CharField(max_length=100)
    client_prenom = models.CharField(max_length=100)

    age = models.IntegerField()
    revenu_mensuel = models.FloatField()
    revolving_utilization = models.FloatField()
    debt_ratio = models.FloatField()
    nb_open_credit_lines = models.IntegerField()
    nb_real_estate_loans = models.IntegerField()
    nb_dependents = models.IntegerField()
    nb_30_59_days_late = models.IntegerField()
    nb_60_89_days_late = models.IntegerField()
    nb_90_days_late = models.IntegerField()

    score_risque = models.FloatField()
    niveau_risque = models.CharField(max_length=20)

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_nom} {self.client_prenom} - {self.score_risque}%"