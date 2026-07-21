from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.http import JsonResponse
from django.db import models as django_models
from collections import Counter
from .models import Conseiller, DossierCredit, LogScoring
from .ocr_utils import extraire_texte, extraire_revenu
from .llm_utils import poser_question_llm
from .shap_utils import expliquer_dossier
from .drift_utils import detecter_drift
import joblib
import pandas as pd
from pathlib import Path
import hashlib



BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / 'xgboost_model.pkl'
model = joblib.load(MODEL_PATH)
def calculer_hash_modele():
    with open(MODEL_PATH, 'rb') as f:
        contenu = f.read()
    return hashlib.md5(contenu).hexdigest()[:10]

VERSION_MODELE_ACTUELLE = calculer_hash_modele()

FEATURE_ORDER = [
    'age', 'revenu_mensuel', 'revolving_utilization', 'debt_ratio',
    'nb_open_credit_lines', 'nb_real_estate_loans', 'nb_dependents',
    'nb_30_59_days_late', 'nb_60_89_days_late', 'nb_90_days_late',
]

MAPPING_HISTORIQUE = {
    'aucun': (0, 0, 0),
    'leger': (1, 0, 0),
    'grave': (0, 1, 2),
}


def est_admin(user):
    return hasattr(user, 'conseiller') and user.conseiller.role == 'admin'


@login_required
def dashboard(request):
    recherche = request.GET.get('q', '').strip()
    dossiers = DossierCredit.objects.all().order_by('-date_creation')

    if recherche:
        dossiers = dossiers.filter(
            django_models.Q(client_nom__icontains=recherche) |
            django_models.Q(client_prenom__icontains=recherche)
        )

    total_dossiers = dossiers.count()
    nb_faible = dossiers.filter(niveau_risque='Faible').count()
    nb_modere = dossiers.filter(niveau_risque='Modéré').count()
    nb_eleve = dossiers.filter(niveau_risque='Élevé').count()

    score_moyen = (sum(d.score_risque for d in dossiers) / total_dossiers) if total_dossiers > 0 else 0
    dossiers_affiches = dossiers if recherche else dossiers[:5]

    context = {
        'total_dossiers': total_dossiers,
        'nb_faible': nb_faible,
        'nb_modere': nb_modere,
        'nb_eleve': nb_eleve,
        'score_moyen': round(score_moyen, 1),
        'derniers_dossiers': dossiers_affiches,
        'recherche': recherche,
    }
    return render(request, 'dashboard.html', context)


@login_required
def nouveau_dossier(request):
    if request.method == 'POST':
        client_nom = request.POST['client_nom']
        client_prenom = request.POST['client_prenom']
        age = float(request.POST['age'])
        revenu_mensuel = float(request.POST['revenu_mensuel'])
        limite_carte = float(request.POST['limite_carte'])
        solde_carte = float(request.POST['solde_carte'])
        mensualites_engagees = float(request.POST['mensualites_engagees'])
        nb_open_credit_lines = float(request.POST['nb_open_credit_lines'])
        nb_real_estate_loans = float(request.POST['nb_real_estate_loans'])
        nb_dependents = float(request.POST['nb_dependents'])
        historique_paiement = request.POST['historique_paiement']

        nb_30_59_days_late, nb_60_89_days_late, nb_90_days_late = MAPPING_HISTORIQUE[historique_paiement]
        revolving_utilization = solde_carte / limite_carte if limite_carte > 0 else 0
        debt_ratio = mensualites_engagees / revenu_mensuel if revenu_mensuel > 0 else 0

        donnees = {
            'age': age, 'revenu_mensuel': revenu_mensuel,
            'revolving_utilization': revolving_utilization, 'debt_ratio': debt_ratio,
            'nb_open_credit_lines': nb_open_credit_lines, 'nb_real_estate_loans': nb_real_estate_loans,
            'nb_dependents': nb_dependents, 'nb_30_59_days_late': nb_30_59_days_late,
            'nb_60_89_days_late': nb_60_89_days_late, 'nb_90_days_late': nb_90_days_late,
        }

        X = pd.DataFrame([donnees])[FEATURE_ORDER]
        proba_defaut = model.predict_proba(X)[0][1]
        score_risque = round(proba_defaut * 100, 1)

        if score_risque < 30:
            niveau = "Faible"
        elif score_risque < 60:
            niveau = "Modéré"
        else:
            niveau = "Élevé"

        conseiller = Conseiller.objects.get(user=request.user)
        dossier = DossierCredit.objects.create(
            conseiller=conseiller, client_nom=client_nom, client_prenom=client_prenom,
            age=age, revenu_mensuel=revenu_mensuel, revolving_utilization=revolving_utilization,
            debt_ratio=debt_ratio, nb_open_credit_lines=nb_open_credit_lines,
            nb_real_estate_loans=nb_real_estate_loans, nb_dependents=nb_dependents,
            nb_30_59_days_late=nb_30_59_days_late, nb_60_89_days_late=nb_60_89_days_late,
            nb_90_days_late=nb_90_days_late, score_risque=score_risque, niveau_risque=niveau,
        )

        LogScoring.objects.create(
            dossier=dossier, conseiller=conseiller,
            score_calcule=score_risque, version_modele=VERSION_MODELE_ACTUELLE,
        )

        context = {'score_risque': score_risque, 'niveau': niveau, 'donnees': donnees, 'dossier': dossier}
        return render(request, 'resultat.html', context)

    return render(request, 'nouveau_dossier.html')


@login_required
def scanner_document(request):
    if request.method == 'POST' and request.FILES.get('document_paie'):
        fichier = request.FILES['document_paie']
        texte = extraire_texte(fichier)
        revenu = extraire_revenu(texte)
        return JsonResponse({'succes': True, 'revenu_detecte': revenu, 'texte_brut': texte[:500]})
    return JsonResponse({'succes': False, 'erreur': 'Aucun fichier reçu'})


@login_required
def chatbot(request, dossier_id):
    dossier = DossierCredit.objects.get(id=dossier_id)
    reponse = None
    question = None

    if request.method == 'POST':
        question = request.POST.get('question')
        reponse = poser_question_llm(question, dossier)

    context = {'dossier': dossier, 'question': question, 'reponse': reponse}
    return render(request, 'chatbot.html', context)


@login_required
def explication_shap(request, dossier_id):
    dossier = DossierCredit.objects.get(id=dossier_id)
    causes_shap = expliquer_dossier(model, dossier)
    return render(request, 'shap.html', {'dossier': dossier, 'causes_shap': causes_shap})


@login_required
@user_passes_test(est_admin)
def administration(request):
    conseillers = Conseiller.objects.all()
    dossiers = DossierCredit.objects.all().order_by('-date_creation')

    total_dossiers = dossiers.count()
    nb_faible = dossiers.filter(niveau_risque='Faible').count()
    nb_modere = dossiers.filter(niveau_risque='Modéré').count()
    nb_eleve = dossiers.filter(niveau_risque='Élevé').count()
    score_moyen = (sum(d.score_risque for d in dossiers) / total_dossiers) if total_dossiers > 0 else 0

    toutes_causes = []
    for d in dossiers:
        toutes_causes.extend(d.generer_causes())
    causes_frequentes = Counter(toutes_causes).most_common(5)

    perf_conseillers = []
    for c in conseillers:
        nb = DossierCredit.objects.filter(conseiller=c).count()
        moy = DossierCredit.objects.filter(conseiller=c).aggregate(django_models.Avg('score_risque'))['score_risque__avg'] or 0
        perf_conseillers.append({'nom': c.user.username, 'nb': nb, 'moy': round(moy, 1)})

    segments_age = {
        '18-30': dossiers.filter(age__gte=18, age__lt=30).count(),
        '30-45': dossiers.filter(age__gte=30, age__lt=45).count(),
        '45-60': dossiers.filter(age__gte=45, age__lt=60).count(),
        '60+': dossiers.filter(age__gte=60).count(),
    }
    segments_revenu = {
        '< 4000 MAD': dossiers.filter(revenu_mensuel__lt=4000).count(),
        '4000-8000 MAD': dossiers.filter(revenu_mensuel__gte=4000, revenu_mensuel__lt=8000).count(),
        '8000-15000 MAD': dossiers.filter(revenu_mensuel__gte=8000, revenu_mensuel__lt=15000).count(),
        '15000+ MAD': dossiers.filter(revenu_mensuel__gte=15000).count(),
    }

    context = {
        'conseillers': conseillers, 'dossiers': dossiers,
        'total_dossiers': total_dossiers, 'nb_faible': nb_faible,
        'nb_modere': nb_modere, 'nb_eleve': nb_eleve,
        'score_moyen': round(score_moyen, 1),
        'causes_frequentes': causes_frequentes,
        'perf_conseillers': perf_conseillers,
        'segments_age': segments_age,
        'segments_revenu': segments_revenu,
    }
    return render(request, 'administration.html', context)


@login_required
@user_passes_test(est_admin)
def simulation_seuil(request):
    nouveau_seuil = float(request.GET.get('seuil', 60))
    dossiers = DossierCredit.objects.all()

    nb_actuellement_eleve = dossiers.filter(niveau_risque='Élevé').count()
    nb_avec_nouveau_seuil = dossiers.filter(score_risque__gte=nouveau_seuil).count()

    context = {
        'nouveau_seuil': nouveau_seuil,
        'nb_actuellement_eleve': nb_actuellement_eleve,
        'nb_avec_nouveau_seuil': nb_avec_nouveau_seuil,
        'difference': nb_avec_nouveau_seuil - nb_actuellement_eleve,
    }
    return render(request, 'simulation_seuil.html', context)


@login_required
@user_passes_test(est_admin)
def monitoring_drift(request):
    dossiers_recents = DossierCredit.objects.all().order_by('-date_creation')[:20]
    resultat = detecter_drift(dossiers_recents)
    return render(request, 'drift.html', {'resultat': resultat})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Conseiller.objects.create(user=user, agence="Agence Casablanca Centre")
            auth_login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})