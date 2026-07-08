"""
ocr_utils.py
------------
Fonctions d'extraction de texte depuis une image (bulletin de paie,
CIN, etc.) via Tesseract OCR, pour pré-remplir le formulaire de dossier.
"""

import pytesseract
from PIL import Image
import re

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\user\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"


def extraire_texte(fichier_image):
    image = Image.open(fichier_image)
    texte = pytesseract.image_to_string(image, lang='fra')
    return texte


def extraire_revenu(texte):
    motif = r'(\d[\d\s]{2,8}[.,]?\d{0,2})\s*(?:MAD|DH|Dirhams?)'
    resultats = re.findall(motif, texte, re.IGNORECASE)

    if resultats:
        montant_brut = resultats[0].replace(' ', '').replace(',', '.')
        try:
            return float(montant_brut)
        except ValueError:
            return None
    return None