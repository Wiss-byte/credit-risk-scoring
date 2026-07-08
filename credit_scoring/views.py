from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from .models import Conseiller, DossierCredit
import joblib
import pandas as pd
from pathlib import Path
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .ocr_utils import extraire_texte, extraire_revenu
from .llm_utils import poser_question_llm

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / 'xgboost_model.pkl'
model = joblib.load(MODEL_PATH)

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


@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

def est_admin(user):
    return hasattr(user, 'conseiller') and user.conseiller.role == 'admin'


@login_required
@user_passes_test(est_admin)
def administration(request):
    conseillers = Conseiller.objects.all()
    dossiers = DossierCredit.objects.all().order_by('-date_creation')
    context = {
        'conseillers': conseillers,
        'dossiers': dossiers,
    }
    return render(request, 'administration.html', context)
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
            'age': age,
            'revenu_mensuel': revenu_mensuel,
            'revolving_utilization': revolving_utilization,
            'debt_ratio': debt_ratio,
            'nb_open_credit_lines': nb_open_credit_lines,
            'nb_real_estate_loans': nb_real_estate_loans,
            'nb_dependents': nb_dependents,
            'nb_30_59_days_late': nb_30_59_days_late,
            'nb_60_89_days_late': nb_60_89_days_late,
            'nb_90_days_late': nb_90_days_late,
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
            conseiller=conseiller,
            client_nom=client_nom,
            client_prenom=client_prenom,
            age=age,
            revenu_mensuel=revenu_mensuel,
            revolving_utilization=revolving_utilization,
            debt_ratio=debt_ratio,
            nb_open_credit_lines=nb_open_credit_lines,
            nb_real_estate_loans=nb_real_estate_loans,
            nb_dependents=nb_dependents,
            nb_30_59_days_late=nb_30_59_days_late,
            nb_60_89_days_late=nb_60_89_days_late,
            nb_90_days_late=nb_90_days_late,
            score_risque=score_risque,
            niveau_risque=niveau,
        )

        context = {
            'score_risque': score_risque,
            'niveau': niveau,
            'donnees': donnees,
            'dossier': dossier,
        }
        return render(request, 'resultat.html', context)

    return render(request, 'nouveau_dossier.html')


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
@login_required
def scanner_document(request):
    if request.method == 'POST' and request.FILES.get('document_paie'):
        fichier = request.FILES['document_paie']
        texte = extraire_texte(fichier)
        revenu = extraire_revenu(texte)

        return JsonResponse({
            'succes': True,
            'revenu_detecte': revenu,
            'texte_brut': texte[:500],
        })

    return JsonResponse({'succes': False, 'erreur': 'Aucun fichier reçu'})
@login_required
def chatbot(request, dossier_id):
    dossier = DossierCredit.objects.get(id=dossier_id)
    reponse = None
    question = None

    if request.method == 'POST':
        question = request.POST.get('question')
        reponse = poser_question_llm(question, dossier)

    context = {
        'dossier': dossier,
        'question': question,
        'reponse': reponse,
    }
    return render(request, 'chatbot.html', context)