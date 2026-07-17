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

    def generer_causes(self):
        causes = []
        if self.nb_90_days_late > 0:
            causes.append("Le client a eu au moins un retard de paiement supérieur à 90 jours — c'est le facteur le plus pénalisant.")
        if self.nb_60_89_days_late > 0:
            causes.append("Le client a eu un retard de paiement entre 60 et 89 jours.")
        if self.nb_30_59_days_late > 0:
            causes.append("Le client a eu un retard de paiement léger (30 à 59 jours).")
        if self.debt_ratio > 0.5:
            causes.append(f"Le ratio d'endettement est élevé ({self.debt_ratio:.0%}) : une grande partie du revenu est déjà engagée dans d'autres charges.")
        if self.revolving_utilization > 0.7:
            causes.append(f"Le client utilise {self.revolving_utilization:.0%} de sa limite de crédit renouvelable, signe de tension financière.")
        if self.nb_dependents > 3:
            causes.append(f"Le client a {self.nb_dependents} personnes à charge, ce qui réduit sa marge financière disponible.")
        if self.revenu_mensuel < 3000:
            causes.append("Le revenu mensuel déclaré est relativement faible.")
        if self.nb_open_credit_lines > 6:
            causes.append(f"Le client a déjà {self.nb_open_credit_lines} lignes de crédit ouvertes, ce qui indique un recours fréquent au crédit.")

        if not causes:
            causes.append("Aucun retard de paiement enregistré.")
            if self.debt_ratio <= 0.3:
                causes.append(f"Le ratio d'endettement est faible ({self.debt_ratio:.0%}), signe d'une bonne capacité de remboursement.")
            if self.revolving_utilization <= 0.3:
                causes.append("Le client utilise peu son crédit renouvelable disponible.")
            if self.revenu_mensuel >= 5000:
                causes.append("Le revenu mensuel est confortable par rapport aux charges.")

        return causes


class LogScoring(models.Model):
    dossier = models.ForeignKey(DossierCredit, on_delete=models.CASCADE, related_name='logs')
    conseiller = models.ForeignKey(Conseiller, on_delete=models.CASCADE)
    score_calcule = models.FloatField()
    version_modele = models.CharField(max_length=50, default='xgboost_v1')
    date_calcul = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.dossier} — {self.date_calcul}"