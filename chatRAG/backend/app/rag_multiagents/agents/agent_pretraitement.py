import os
import psycopg2
import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

# === Configuration de la base de données PostgreSQL ===

# Récupération du mot de passe via les variables d’environnement
PG_PASSWORD = os.getenv("PG_PASSWORD")

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": PG_PASSWORD,
    "host": "127.0.0.1",
    "port": "5432"
}

# === Chemins pour sauvegarder l'index FAISS et les textes associés ===
FAISS_INDEX_PATH = "backend/app/rag_multiagents/faiss_index/index.faiss"
TEXTS_PATH = "backend/app/rag_multiagents/faiss_index/texts.pkl"

# === Initialisation du modèle d’embedding ===

# Modèle anglais compact et rapide
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
# Pour du multilingue : paraphrase-multilingual-mpnet-base-v2

embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

# === Initialisation du text splitter ===
# Divise le texte en petits morceaux avec un chevauchement pour le contexte
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        # Taille maximale des chunks en caractères
    chunk_overlap=100,     # Chevauchement entre les chunks
    separators=["\n\n", "\n", ".", ",", " ", ""]  # Ordre de découpe
)

# === Connexion à PostgreSQL ===
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("Connexion à PostgreSQL réussie.")
except Exception as e:
    print(f"Erreur de connexion à PostgreSQL : {e}")
    exit()

# === Fonction de découpage du texte brut ===

def chunk_text(content, doc_id):
    """
    Découpe un texte brut en petits segments appelés "chunks" utilisables pour l’indexation vectorielle.

    Args:
        content (str): Texte brut.
        doc_id (int): ID du document d’origine.

    Returns:
        List[Dict]: Liste de dictionnaires avec doc_id et texte chunké.
    """
    raw_chunks = text_splitter.create_documents([content])
    return [{"doc_id": doc_id, "text": chunk.page_content} for chunk in raw_chunks]

# === Fonction de génération des embeddings ===

def embed_chunks(chunks):
    """
    Génére les vecteurs (embeddings) pour chaque chunk de texte.

    Args:
        chunks (List[Dict]): Liste de chunks.

    Returns:
        Tuple[np.ndarray, List[str]]: Vecteurs normalisés + textes d’origine.
    """
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedding_model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True
    )
    return embeddings, texts

# === Création d’un index FAISS ===

def create_faiss_index(embeddings):
    """
    Crée un index FAISS basé sur la similarité de produit scalaire (cosinus pour vecteurs normalisés).

    Args:
        embeddings (np.ndarray): Matrice des vecteurs.

    Returns:
        faiss.IndexFlatIP: Index FAISS prêt pour la recherche.
    """
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index

# === Récupération des documents liés à une conversation ===

def fetch_documents_by_conversation(conversation_id):
    """
    Récupère tous les documents non vides liés à une conversation.

    Args:
        conversation_id (str): ID de la conversation.

    Returns:
        List[Tuple[int, str]]: Liste de tuples (document_id, contenu).
    """
    try:
        cursor.execute("""
            SELECT id, content 
            FROM documents 
            WHERE conversation_id = %s AND content IS NOT NULL
        """, (conversation_id,))
        results = cursor.fetchall()
        documents = [(doc_id, content) for doc_id, content in results]
        return documents
    except Exception as e:
        print(f"Erreur lors de la récupération des documents pour la conversation {conversation_id} : {e}")
        return []

# === Sauvegarde de l’index FAISS et des textes ===

def save_index_for_conversation(conversation_id, index, texts):
    """
    Sauvegarde l’index FAISS (.faiss) et les textes originaux (.pkl) dans un dossier dédié à la conversation.

    Args:
        conversation_id (str): ID de la conversation.
        index (faiss.Index): Index FAISS.
        texts (List[str]): Textes correspondants aux vecteurs.
    """
    folder_path = f"backend/app/rag_multiagents/faiss_index/{conversation_id}"
    os.makedirs(folder_path, exist_ok=True)

    faiss_path = os.path.join(folder_path, "index.faiss")
    texts_path = os.path.join(folder_path, "texts.pkl")

    faiss.write_index(index, faiss_path)
    with open(texts_path, "wb") as f:
        pickle.dump(texts, f)

    print(f"Index sauvegardé pour la conversation '{conversation_id}'.")

# === Pipeline principal : découpage, vectorisation, indexation ===

def run_preprocessing(conversation_id):
    """
    Pipeline principal :
    - Récupère les documents liés à une conversation
    - Découpe le texte en chunks
    - Génère les embeddings
    - Crée l’index FAISS
    - Sauvegarde les résultats

    Args:
        conversation_id (str): ID de la conversation à traiter.
    """
    print(f"Récupération des documents pour la conversation '{conversation_id}'...")
    documents = fetch_documents_by_conversation(conversation_id)
    if not documents:
        print(f"Aucun document trouvé pour la conversation {conversation_id}.")
        return

    print(f"Traitement de la conversation '{conversation_id}'...")

    all_chunks = []
    for doc_id, content in documents:
        all_chunks.extend(chunk_text(content, doc_id))

    print(f"Embedding de {len(all_chunks)} chunks...")
    embeddings, texts = embed_chunks(all_chunks)
    embeddings = np.array(embeddings)

    index = create_faiss_index(embeddings)

    print("Sauvegarde de l'index FAISS...")
    save_index_for_conversation(conversation_id, index, texts)

    print(f"Prétraitement terminé pour la conversation {conversation_id}.")

# === Exécution de test ===

if __name__ == "__main__":
    # ID de conversation à traiter (doit exister dans la base de données)
    conversation_id = '1'
    run_preprocessing(conversation_id)

    # Fermeture des connexions à la base
    cursor.close()
    conn.close()
    print("Connexions fermées.")
