# === Imports des modules locaux ===
from agent_recherche import search
from agent_conversation import save_conversation, get_conversation_history

# Import de l’agent local (LLM exécuté en local)
from agent_generation_local import (
    choisir_modele as choisir_modele_local,
    charger_modele,
    generer_reponse as generer_reponse_local
)

# Import de l’agent distant (LLM via API Hugging Face)
from agent_generation_enligne import (
    generer_reponse as generer_reponse_enligne,
    choisir_modele_enligne
)

# === Choix de l'agent : local ou distant ===
def choisir_agent():
    """
    Affiche un menu pour choisir entre agent local (LLM en local)
    ou agent distant (via API Hugging Face).
    
    Returns:
        int: 1 pour local, 2 pour distant
    """
    print("\n=== Choix de l'agent ===")
    print("1. Agent local (LLM sur votre machine)")
    print("2. Agent en ligne (via API Hugging Face)")
    while True:
        try:
            choix = int(input("Choisissez un agent (1 ou 2) : "))
            if choix in [1, 2]:
                return choix
            else:
                print("Choix invalide.")
        except ValueError:
            print("Entrée non valide.")

# === Pose une question avec un agent local ===
def poser_question_local(user_id, question, llm, conversation_id):
    """
    Pose une question en utilisant un modèle local.

    Args:
        user_id (int): ID utilisateur
        question (str): Question posée
        llm: Modèle local chargé
        conversation_id (int): ID de la conversation en cours

    Returns:
        str: Réponse générée
    """
    try:
        conversation_id = int(conversation_id)
    except ValueError:
        print("Erreur: L'ID de conversation pour l'agent local doit être un entier.")
        return "Erreur: ID de conversation invalide."

    # Recherche contextuelle (RAG)
    contextes = search(question, conversation_id, top_k=3)
    contexte_concatene = "\n".join([c['texte'] for c in contextes]) if contextes else "Aucun"
    
    # Génération de la réponse avec le LLM local
    reponse = generer_reponse_local(llm, contexte_concatene, question)
    
    # Sauvegarde dans l’historique
    save_conversation(user_id, conversation_id, question, reponse)
    return reponse

# === Pose une question avec un agent en ligne ===
def poser_question_enligne(user_id, question, conversation_id, api_url):
    """
    Pose une question en utilisant un modèle distant via API.

    Args:
        user_id (int): ID utilisateur
        question (str): Question posée
        conversation_id (int): ID de la conversation
        api_url (str): URL de l'API Hugging Face

    Returns:
        str: Réponse générée
    """
    try:
        conversation_id = int(conversation_id) 
    except ValueError:
        print("Erreur: L'ID de conversation pour l'agent en ligne doit être un entier.")
        return "Erreur: ID de conversation invalide."

    # Recherche contextuelle (RAG)
    print(f"DEBUG: Calling search with query='{question}', conversation_id={conversation_id}, top_k=3")
    contextes = search(question, conversation_id, top_k=3)

    contexte_concatene = "\n".join([c['texte'] for c in contextes]) if contextes else "Aucun"
    
    # Génération via API distante
    reponse = generer_reponse_enligne(contexte_concatene, question, api_url) 
    
    # Sauvegarde dans l’historique
    save_conversation(user_id, conversation_id, question, reponse)
    return reponse

# === Affiche l'historique d'une conversation ===
def afficher_historique(user_id, conversation_id):
    """
    Affiche l’historique des échanges entre utilisateur et bot.

    Args:
        user_id (int): ID utilisateur
        conversation_id (int): ID de la conversation
    """
    try:
        conversation_id = int(conversation_id) 
    except ValueError:
        print("Erreur: L'ID de conversation pour l'affichage de l'historique doit être un entier.")
        return 

    historique = get_conversation_history(user_id, conversation_id)
    print("\nHistorique des conversations :\n")
    if not historique:
        print("Aucun historique pour cette conversation.")
        return

    for msg, rep, ts in historique:
        print(f"[{ts.strftime('%Y-%m-%d %H:%M:%S')}]")
        print(f"Utilisateur : {msg}")
        print(f"Bot         : {rep}\n")

# === Point d'entrée principal ===
if __name__ == "__main__":
    user_id = 1  # ID utilisateur fixe (peut être modifié pour multi-utilisateurs)

    agent_type = choisir_agent()

    # Demande l'ID de la conversation à l'utilisateur
    while True:
        try:
            conversation_id_input = input("Entrez l'ID de la conversation actuelle: ")
            conversation_id = int(conversation_id_input)
            break
        except ValueError:
            print("Entrée non valide. Veuillez entrer un nombre entier pour l'ID de conversation.")

    # === Initialisation selon l'agent choisi ===
    llm = None 
    api_url = None 

    if agent_type == 1:  # Agent local
        nom_modele, chemin = choisir_modele_local()
        llm = charger_modele(chemin)
        agent_function = lambda q: poser_question_local(user_id, q, llm, conversation_id)
    
    else:  # Agent distant
        api_url = choisir_modele_enligne()
        agent_function = lambda q: poser_question_enligne(user_id, q, conversation_id, api_url)

    # === Boucle d’interaction principale ===
    print("\nBienvenue dans le chatbot RAG.")
    print("Tapez 'exit' pour quitter, ou 'historique' pour voir les anciens échanges.")

    while True:
        user_input = input("Vous: ")
        if user_input.lower() == "exit":
            print("Fin de la session.")
            break
        elif user_input.lower() == "historique":
            afficher_historique(user_id, conversation_id)
        else:
            response = agent_function(user_input)
            print("Bot:", response)
