import os
from huggingface_hub import InferenceClient
from models_config_enligne import MODELS_ENLIGNE  # Dictionnaire contenant les informations des modèles disponibles

# Initialise le client Hugging Face avec la clé API depuis la variable d'environnement
client = InferenceClient(api_key=os.getenv("HF_token"))


def choisir_modele_enligne():
    """
    Affiche la liste des modèles disponibles définis dans MODELS_ENLIGNE,
    et invite l'utilisateur à en sélectionner un.

    Retourne :
        str : L'identifiant (`model_id`) du modèle choisi.
    """
    print("\n=== Modèles en ligne disponibles ===")
    for i, m in MODELS_ENLIGNE.items():
        print(f"{i}. {m['nom']}")

    while True:
        try:
            choix = int(input("Choisissez un modèle (numéro) : "))
            if choix in MODELS_ENLIGNE:
                return MODELS_ENLIGNE[choix]["model_id"]
            else:
                print("Choix invalide. Veuillez entrer un numéro correspondant à la liste.")
        except ValueError:
            print("Entrée non valide. Veuillez entrer un nombre entier.")


def generer_reponse(context, question, model_id):
    """
    Génère une réponse à partir d'un contexte et d'une question en utilisant un modèle distant via Hugging Face.

    Args:
        context (str): Le texte contextuel sur lequel l'assistant doit se baser.
        question (str): La question posée par l'utilisateur.
        model_id (str): L'identifiant du modèle à utiliser.

    Retourne :
        str : La réponse générée par le modèle ou un message d'erreur.
    """
    # Construction du prompt pour guider le comportement du modèle
    prompt = f"""Tu es un assistant intelligent. Réponds à la question en te basant uniquement sur le contexte suivant.
Contexte : {context}

Question : {question}

Instructions :
- Si la réponse ne figure pas dans le contexte, indique-le clairement.
- Si la question est générale et ne nécessite pas le contexte, donne une réponse appropriée basée sur tes connaissances.
- Ne fais pas de suppositions.
- Réponds dans la même langue que la question.

Réponse :
"""
    try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        return completion.choices[0].message["content"].strip()
    except Exception as e:
        return f"Erreur lors de l'appel API : {e}"


if __name__ == "__main__":
    # Exemple de test interactif
    model_id = choisir_modele_enligne()
    contexte = "Le capital de la SOCIÉTÉ DES BOISSONS DU MAROC est 102.7 MDH."
    question = "Quelle est le capital de la SOCIÉTÉ DES BOISSONS DU MAROC ?"
    reponse = generer_reponse(contexte, question, model_id)
    print("\nRéponse générée :\n", reponse)
