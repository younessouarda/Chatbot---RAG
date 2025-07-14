import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

# Initialisation du modèle d'embedding pour la requête
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

def load_index(conversation_id):
    """
    Charge l'index FAISS et les textes pour une conversation spécifique.
    
    Args:
        conversation_id (int ou str): Identifiant de la conversation.
    
    Returns:
        tuple: L'index FAISS chargé et la liste des textes correspondants.
    
    Raises:
        FileNotFoundError: Si les fichiers index ou textes n'existent pas pour la conversation donnée.
    """
    index_path = f"backend/app/rag_multiagents/faiss_index/{conversation_id}/index.faiss"
    texts_path = f"backend/app/rag_multiagents/faiss_index/{conversation_id}/texts.pkl"

    # Vérification de l'existence des fichiers
    if not os.path.exists(index_path) or not os.path.exists(texts_path):
        raise FileNotFoundError(f"Index ou textes manquants pour la conversation : {conversation_id}")

    # Chargement de l'index FAISS
    index = faiss.read_index(index_path)
    # Chargement des textes chunkés
    with open(texts_path, "rb") as f:
        texts = pickle.load(f)

    return index, texts

def embed_query(query):
    """
    Génère l'embedding normalisé pour la requête utilisateur.
    
    Args:
        query (str): Texte de la requête utilisateur.
    
    Returns:
        np.ndarray: Embedding vectoriel normalisé correspondant à la requête.
    """
    query_embedding = embedding_model.encode([query], normalize_embeddings=True)
    return query_embedding

def search(query, conversation_id, top_k=5, similarity_threshold=0.75, context_window=1, doc_length_threshold=1000):
    """
    Effectue une recherche sémantique avec extension contextuelle autour des résultats.
    
    Args:
        query (str): Requête utilisateur à rechercher.
        conversation_id (int ou str): ID de la conversation pour charger le bon index.
        top_k (int): Nombre maximum de résultats à retourner.
        similarity_threshold (float): Seuil minimal de similarité pour retenir un résultat.
        context_window (int): Nombre de chunks avant et après à inclure autour du chunk pertinent.
        doc_length_threshold (int): Taille minimale du document pour appliquer la recherche, sinon on retourne tout.
    
    Returns:
        list of dict ou None: Liste de dictionnaires avec le texte trouvé sous la clé 'texte', ou None si aucun résultat.
    """
    try:
        # Chargement de l'index et des textes chunkés
        index, texts = load_index(conversation_id)
    except FileNotFoundError as e:
        print(e)
        return None

    # Calcul de l'embedding de la requête
    query_embedding = embed_query(query)

    # Recherche dans l'index FAISS
    distances, indices = index.search(query_embedding, top_k)

    relevant_texts = []
    seen_indices = set()

    # Concaténation de tout le texte pour vérifier la longueur globale
    full_text = "\n".join(texts)
    if len(full_text) < doc_length_threshold:
        print("Document trop court, retour du texte complet.")
        return [{"texte": full_text}]

    # Parcours des résultats obtenus
    for i, distance in enumerate(distances[0]):
        # On ne garde que les résultats au-dessus du seuil de similarité
        if distance >= similarity_threshold:
            idx = indices[0][i]
            if idx not in seen_indices:
                # Extension du contexte autour du chunk pertinent
                start = max(0, idx - context_window)
                end = min(len(texts), idx + context_window + 1)
                expanded_text = " ".join(texts[start:end])
                relevant_texts.append((expanded_text, distance))
                # On marque les indices inclus pour éviter les doublons
                seen_indices.update(range(start, end))

    # Si aucun texte pertinent n'a été trouvé
    if not relevant_texts:
        print("Aucun résultat pertinent trouvé même après extension.")
        return None

    # Tri des résultats par similarité décroissante (distance croissante)
    relevant_texts.sort(key=lambda x: x[1])

    # Affichage des résultats pour information
    print(f"Résultats pour la conversation {conversation_id} (top {top_k}):")
    for i, (text, distance) in enumerate(relevant_texts[:top_k]):
        print(f"{i + 1}. (similarité : {1 - distance:.4f}) | Chunk étendu de longueur {len(text)}")

    # Retour des résultats sous forme de liste de dictionnaires
    return [{"texte": text} for text, _ in relevant_texts[:top_k]]
