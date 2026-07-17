"""
llm_utils.py
------------
Fonctions pour dialoguer avec un modèle LLM local via Ollama,
dans le contexte d'un dossier de crédit précis.
"""

import requests
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


def nettoyer_reponse(texte):
    """
    Retire la syntaxe Markdown basique que le LLM ajoute parfois
    (gras, italique, titres) pour un affichage HTML propre en texte brut.
    """
    texte = re.sub(r'\*\*(.*?)\*\*', r'\1', texte)
    texte = re.sub(r'\*(.*?)\*', r'\1', texte)
    texte = re.sub(r'#{1,6}\s*', '', texte)
    texte = re.sub(r'`(.*?)`', r'\1', texte)
    return texte.strip()


def poser_question_llm(question, dossier):
    """
    Envoie une question au LLM local, avec le contexte du dossier
    crédit injecté dans le prompt, et retourne la réponse texte.
    """
    contexte = f"""Tu es un assistant qui aide un conseiller bancaire EQDOM
à analyser un dossier de crédit. Voici les informations du dossier :

- Client : {dossier.client_nom} {dossier.client_prenom}
- Âge : {dossier.age} ans
- Revenu mensuel : {dossier.revenu_mensuel} MAD
- Taux d'utilisation du crédit renouvelable : {dossier.revolving_utilization:.2f}
- Ratio d'endettement : {dossier.debt_ratio:.2f}
- Nombre de lignes de crédit ouvertes : {dossier.nb_open_credit_lines}
- Nombre de prêts immobiliers : {dossier.nb_real_estate_loans}
- Personnes à charge : {dossier.nb_dependents}
- Score de risque calculé : {dossier.score_risque}%
- Niveau de risque : {dossier.niveau_risque}

Question du conseiller : {question}

Réponds de manière concise et professionnelle, en te basant uniquement
sur les données du dossier ci-dessus."""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": contexte,
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        reponse_brute = response.json().get("response", "Pas de réponse générée.")
        return nettoyer_reponse(reponse_brute)

    except requests.exceptions.ConnectionError:
        return "Erreur : Ollama n'est pas accessible. Vérifie qu'il tourne (commande : ollama serve)."
    except requests.exceptions.Timeout:
        return "Erreur : le modèle met trop de temps à répondre."
    except Exception as e:
        return f"Erreur inattendue : {e}"