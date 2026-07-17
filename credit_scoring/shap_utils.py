import shap
import pandas as pd

FEATURE_ORDER = [
    'age', 'revenu_mensuel', 'revolving_utilization', 'debt_ratio',
    'nb_open_credit_lines', 'nb_real_estate_loans', 'nb_dependents',
    'nb_30_59_days_late', 'nb_60_89_days_late', 'nb_90_days_late',
]

FEATURE_LABELS = {
    'age': "Âge",
    'revenu_mensuel': "Revenu mensuel",
    'revolving_utilization': "Taux d'utilisation du crédit renouvelable",
    'debt_ratio': "Ratio d'endettement",
    'nb_open_credit_lines': "Nombre de lignes de crédit ouvertes",
    'nb_real_estate_loans': "Prêts immobiliers en cours",
    'nb_dependents': "Personnes à charge",
    'nb_30_59_days_late': "Retards 30-59 jours",
    'nb_60_89_days_late': "Retards 60-89 jours",
    'nb_90_days_late': "Retards 90+ jours",
}


def expliquer_dossier(model, dossier):
    donnees = pd.DataFrame([{
        'age': dossier.age,
        'revenu_mensuel': dossier.revenu_mensuel,
        'revolving_utilization': dossier.revolving_utilization,
        'debt_ratio': dossier.debt_ratio,
        'nb_open_credit_lines': dossier.nb_open_credit_lines,
        'nb_real_estate_loans': dossier.nb_real_estate_loans,
        'nb_dependents': dossier.nb_dependents,
        'nb_30_59_days_late': dossier.nb_30_59_days_late,
        'nb_60_89_days_late': dossier.nb_60_89_days_late,
        'nb_90_days_late': dossier.nb_90_days_late,
    }])[FEATURE_ORDER]

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(donnees)[0]

    paires = list(zip(FEATURE_ORDER, shap_values))
    paires.sort(key=lambda x: abs(x[1]), reverse=True)

    phrases = []
    for feature, valeur in paires[:4]:
        label = FEATURE_LABELS[feature]
        if valeur > 0:
            phrases.append(f"{label} augmente le risque (contribution : +{valeur:.3f})")
        else:
            phrases.append(f"{label} réduit le risque (contribution : {valeur:.3f})")

    return phrases