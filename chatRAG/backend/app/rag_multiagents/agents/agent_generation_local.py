import os
import requests
from llama_cpp import Llama
from models_config_local import MODEL_INFOS  # Dictionnaire contenant les infos des modèles (nom, URL, nom de fichier)

# Répertoire de stockage des modèles
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

# === TÉLÉCHARGEMENT SIMPLE ===

def download_model(filename, url):
    """
    Télécharge un modèle si celui-ci n'est pas déjà présent localement.

    Args:
        filename (str): Nom du fichier à sauvegarder.
        url (str): URL de téléchargement du modèle.

    Retourne :
        str : Chemin local vers le modèle.
    """
    model_path = os.path.join(MODEL_DIR, filename)
    if os.path.exists(model_path):
        print(f"Modèle déjà présent : {filename}")
        return model_path

    print(f"Téléchargement du modèle {filename}...")
    os.makedirs(MODEL_DIR, exist_ok=True)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(model_path, 'wb') as f:
            total = 0
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
                    print(f"\rTéléchargé : {round(total / 1024 / 1024, 2)} Mo", end="")
    print("\nTéléchargement terminé.")
    return model_path

# === TÉLÉCHARGEMENT AVEC ÉTAT & ANNULATION ===

DOWNLOAD_STATUS = {}  # Stocke l'état de téléchargement de chaque modèle

def download_model_with_progress(model_name, url, filename, cancel_event):
    """
    Télécharge un modèle avec suivi de progression et possibilité d'annulation.

    Args:
        model_name (str): Nom du modèle (clé unique).
        url (str): URL du modèle.
        filename (str): Nom du fichier à créer.
        cancel_event (threading.Event): Permet d’annuler le téléchargement.
    """
    model_path = os.path.join(MODEL_DIR, filename)

    DOWNLOAD_STATUS[model_name] = {
        'status': 'downloading',
        'downloaded_bytes': 0,
        'total_bytes': 0,
        'cancel_event': cancel_event
    }

    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            DOWNLOAD_STATUS[model_name]['total_bytes'] = total_size

            os.makedirs(MODEL_DIR, exist_ok=True)

            with open(model_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if cancel_event.is_set():
                        print(f"Téléchargement du modèle {model_name} annulé.")
                        DOWNLOAD_STATUS[model_name]['status'] = 'cancelled'
                        if os.path.exists(model_path):
                            os.remove(model_path)
                        return
                    
                    f.write(chunk)
                    DOWNLOAD_STATUS[model_name]['downloaded_bytes'] += len(chunk)

        DOWNLOAD_STATUS[model_name]['status'] = 'completed'
        print(f"Téléchargement du modèle {model_name} terminé avec succès.")

    except requests.exceptions.RequestException as e:
        print(f"Erreur lors du téléchargement de {model_name} : {e}")
        DOWNLOAD_STATUS[model_name]['status'] = 'failed'
        if os.path.exists(model_path):
            os.remove(model_path)
    except Exception as e:
        print(f"Erreur inattendue pendant le téléchargement de {model_name} : {e}")
        DOWNLOAD_STATUS[model_name]['status'] = 'failed'
        if os.path.exists(model_path):
            os.remove(model_path)


# === CHOIX & CHARGEMENT DU MODÈLE ===

def choisir_modele():
    """
    Affiche la liste des modèles disponibles et permet à l'utilisateur d'en choisir un.

    Retourne :
        tuple : (nom du modèle, chemin local du fichier modèle)
    """
    print("=== Modèles disponibles ===")
    noms = list(MODEL_INFOS.keys())
    for i, name in enumerate(noms):
        print(f"{i + 1}. {name}")

    while True:
        try:
            choix = int(input("Choisissez un modèle (numéro) : ")) - 1
            if 0 <= choix < len(noms):
                break
            else:
                print("Choix invalide, réessayez.")
        except ValueError:
            print("Entrée invalide, veuillez entrer un numéro.")

    nom_modele = noms[choix]
    info = MODEL_INFOS[nom_modele]
    path = download_model(info['filename'], info['url'])
    return nom_modele, path

def charger_modele(model_path):
    """
    Charge un modèle local avec Llama.cpp.

    Args:
        model_path (str): Chemin local du modèle à charger.

    Retourne :
        Llama : Objet modèle prêt à l’emploi.
    """
    print(f"Chargement du modèle depuis {model_path} ...")
    return Llama(
        model_path=model_path,
        n_ctx=2048,
        n_threads=4,
        verbose=False
    )


# === GÉNÉRATION DE RÉPONSES ===

def generer_reponse(llm, contexte, question):
    """
    Génère une réponse en utilisant le contexte, mais autorise des compléments si nécessaire.

    Args:
        llm (Llama): Instance du modèle.
        contexte (str): Texte contextuel.
        question (str): Question posée.

    Retourne :
        str : Réponse générée.
    """
    prompt = f"""[INST] Utilise ce contexte pour répondre à la question.

IMPORTANT : Réponds dans la même langue que la question.

Contexte : {contexte}

Si l'information n'existe pas dans le contexte, tu peux utiliser tes connaissances,
mais précise que l'information n'est pas mentionnée dans le contexte fourni.

Question : {question}
Réponse : [/INST]"""

    output = llm(prompt, max_tokens=512, stop=["</s>"], temperature=0.7)
    return output["choices"][0]["text"].strip()

def generer_reponse_strict(llm, contexte, question):
    """
    Génère une réponse stricte, uniquement basée sur le contexte fourni.

    Args:
        llm (Llama): Modèle LLM chargé.
        contexte (str): Texte de référence.
        question (str): Question à laquelle répondre.

    Retourne :
        str : Réponse générée.
    """
    prompt = f"""[INST] Tu dois répondre uniquement en utilisant les informations du contexte.
N'utilise pas tes propres connaissances, même si tu crois que la réponse est évidente.
Si la réponse n'est pas dans le contexte, ou si le contexte est vide, dis : "Je ne sais pas".
IMPORTANT : Réponds dans la même langue que la question.

Contexte :
{contexte}

Question : {question}
Réponse : [/INST]"""

    output = llm(prompt, max_tokens=512, stop=["</s>"], temperature=0.0)
    return output["choices"][0]["text"].strip()


# === EXÉCUTION DE TEST ===

if __name__ == "__main__":
    nom_modele, chemin = choisir_modele()
    llm = charger_modele(chemin)

    print("\n=== Test ===")
    contexte_exemple = "le capital de la SOCIÉTÉ DES BOISSONS DU MAROC est 102.7 MDH"
    question_exemple = "Quelle est le capital de la SOCIÉTÉ DES BOISSONS DU MAROC?"

    reponse = generer_reponse_strict(llm, contexte_exemple, question_exemple)
    print(f"\n[{nom_modele}] Réponse générée :\n{reponse}")
