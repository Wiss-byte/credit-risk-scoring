import pandas as pd
from scipy import stats

FEATURES_A_SURVEILLER = ['age', 'revenu_mensuel', 'debt_ratio', 'revolving_utilization']


def detecter_drift(dossiers_recents, dataset_entrainement_path='ml/eqdom_dataset.csv'):
    df_train = pd.read_csv(dataset_entrainement_path)
    resultats = {}

    df_recent = pd.DataFrame([{
        'age': d.age,
        'revenu_mensuel': d.revenu_mensuel,
        'debt_ratio': d.debt_ratio,
        'revolving_utilization': d.revolving_utilization,
    } for d in dossiers_recents])

    if len(df_recent) < 5:
        return {'alerte': False, 'message': 'Pas assez de dossiers récents pour analyser le drift (minimum 5).'}

    for feature in FEATURES_A_SURVEILLER:
        stat, p_value = stats.ks_2samp(df_train[feature], df_recent[feature])
        resultats[feature] = {
            'p_value': round(p_value, 4),
            'drift_detecte': p_value < 0.05,
        }

    drift_global = any(r['drift_detecte'] for r in resultats.values())
    return {'alerte': drift_global, 'details': resultats}