import psycopg2
from minio import Minio
import os
import PyPDF2
import csv
import docx
import openpyxl

# === Configuration de la base de données PostgreSQL ===

# Récupère le mot de passe depuis une variable d'environnement (meilleure pratique que le hardcoding)
PG_PASSWORD = os.getenv("PG_PASSWORD")

DB_CONFIG = {
    "dbname": "postgres",         # Nom de la base
    "user": "postgres",           # Nom d'utilisateur PostgreSQL
    "password": PG_PASSWORD,      # Mot de passe récupéré depuis les variables d'environnement
    "host": "127.0.0.1",          # Hôte (ici localhost)
    "port": "5432"                # Port PostgreSQL
}

# Connexion à PostgreSQL
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("Connexion à PostgreSQL réussie.")

except Exception as e:
    print(f"Erreur de connexion à PostgreSQL : {e}")
    exit()


# === Configuration du client MinIO ===

# Récupère le mot de passe MinIO via variable d'environnement
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")

MINIO_CONFIG = {
    "endpoint": "127.0.0.1:9000",     # Adresse du service MinIO
    "access_key": "admin",           # Clé d'accès (admin par défaut)
    "secret_key": MINIO_ROOT_PASSWORD, # Mot de passe MinIO
    "secure": False                  # Connexion non sécurisée (http)
}

# Connexion au client MinIO
try:
    minio_client = Minio(**MINIO_CONFIG)
    print("Connexion à MinIO réussie.")

except Exception as e:
    print(f"Erreur de connexion à MinIO : {e}")
    exit()

# Nom du bucket MinIO utilisé pour stocker les fichiers
BUCKET_NAME = "documents-storage"

# Vérifie si le bucket existe ; sinon le crée
if not minio_client.bucket_exists(BUCKET_NAME):
    minio_client.make_bucket(BUCKET_NAME)
    print(f"Bucket '{BUCKET_NAME}' créé avec succès.")
else:
    print(f"Bucket '{BUCKET_NAME}' déjà existant.")


# === Fonction d'extraction de texte brut à partir d'un fichier ===

def extract_text(file_path):
    """
    Extrait le contenu textuel brut d’un fichier en fonction de son extension.
    Prend en charge : PDF, TXT, CSV, DOCX, XLSX.
    
    Args:
        file_path (str): Chemin vers le fichier local.

    Returns:
        str or None: Texte extrait du fichier, ou None si erreur ou format non pris en charge.
    """
    text = ""
    file_extension = file_path.split('.')[-1].lower()

    try:
        if file_extension == "pdf":
            with open(file_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"

        elif file_extension == "txt":
            with open(file_path, "r", encoding="utf-8") as txt_file:
                text = txt_file.read()

        elif file_extension == "csv":
            with open(file_path, "r", encoding="utf-8") as csv_file:
                reader = csv.reader(csv_file)
                text = "\n".join([", ".join(row) for row in reader])

        elif file_extension == "docx":
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])

        elif file_extension == "xlsx":
            wb = openpyxl.load_workbook(file_path)
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    text += "\t".join([str(cell) if cell else "" for cell in row]) + "\n"

        else:
            print(f"Format {file_extension.upper()} non supporté pour l'extraction de texte.")
            return None

        return text.strip()

    except Exception as e:
        print(f"Erreur d'extraction du texte : {e}")
        return None


# === Fonction pour uploader un document sur MinIO + insertion en base PostgreSQL ===

def upload_document(file_path, conversation_id, user_id):
    """
    Upload un fichier vers MinIO et stocke les métadonnées + texte brut dans PostgreSQL.

    Args:
        file_path (str): Chemin local du fichier à uploader.
        conversation_id (str): ID de la conversation liée au fichier.
        user_id (str): Identifiant de l'utilisateur ayant uploadé le document.
    """
    if not os.path.exists(file_path):
        print(f"Fichier '{file_path}' introuvable.")
        return
    
    file_name = os.path.basename(file_path)
    file_extension = file_name.split(".")[-1].lower()

    try:
        # Upload du fichier dans MinIO
        minio_client.fput_object(BUCKET_NAME, file_name, file_path)
        print(f"Document '{file_name}' stocké dans MinIO.")

        # Extraction du contenu si format pris en charge
        extracted_text = extract_text(file_path) if file_extension in ["pdf", "txt", "csv", "docx", "xlsx"] else None

        # Insertion dans la table PostgreSQL "documents"
        cursor.execute("""
            INSERT INTO documents (filename, bucket, file_type, content, conversation_id, utilisateur_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (file_name, BUCKET_NAME, file_extension, extracted_text, conversation_id, user_id))
        
        conn.commit()
        print(f"Document '{file_name}' enregistré avec la conversation '{conversation_id}'.")

    except Exception as e:
        print(f"Erreur lors de l'upload : {e}")


# === Bloc principal de test ===

if __name__ == "__main__":
    # Upload de test d’un fichier PDF avec conversation_id défini
    upload_document("cp_sbm_t1_2025.pdf", "conv_abc123", "admin")

    # Fermeture propre des connexions
    cursor.close()
    conn.close()
    print("Connexions fermées.")
