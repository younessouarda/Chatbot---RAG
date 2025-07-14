# Importation des bibliothèques nécessaires
import os
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_cors import CORS
from werkzeug.utils import secure_filename
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)

import threading  # Pour gérer les téléchargements en arrière-plan
import requests  # Pour effectuer des requêtes HTTP (ex: téléchargement de modèles)
import json  # Pour manipuler des données JSON si nécessaire


# Chargement des variables d'environnement à partir du fichier .env
load_dotenv()

# Initialisation de l'application Flask
app = Flask(__name__)
CORS(app)  # Activation du Cross-Origin Resource Sharing pour les requêtes depuis le front-end
bcrypt = Bcrypt(app)  # Initialisation du module de hachage de mots de passe


# Configuration de JWT (JSON Web Token) pour l'authentification
app.config["JWT_SECRET_KEY"] = "Yo@120083561oY"  # Clé secrète pour signer les tokens JWT (à sécuriser en prod)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)  # Durée de validité d'un token (1 jour)
app.config["JWT_ERROR_MESSAGE_KEY"] = "description"  # Clé pour les messages d'erreur JWT personnalisés

jwt = JWTManager(app)  # Initialisation du gestionnaire JWT


# Gestionnaires personnalisés des erreurs JWT

@jwt.unauthorized_loader
def unauthorized_response(callback):
    """
    S'exécute lorsque l'authentification échoue car aucun token JWT n'est fourni.
    Exemple: Missing Authorization Header.
    """
    print(f"JWT Unauthorized Error: {callback}")
    return jsonify({"error": "Échec de l'authentification", "details": "Le jeton est manquant ou mal formé."}), 401


@jwt.invalid_token_loader
def invalid_token_response(callback):
    """
    S'exécute si un token JWT est fourni mais est invalide (ex: signature incorrecte).
    """
    print(f"JWT Invalid Token Error: {callback}")
    return jsonify({"error": "Échec de l'authentification", "details": "Le jeton est invalide."}), 401


@jwt.expired_token_loader
def expired_token_response(jwt_header, jwt_data):
    """
    S'exécute si un token JWT est expiré.
    """
    print(f"JWT Expired Token Error: {jwt_header}, {jwt_data}")
    return jsonify({"error": "Échec de l'authentification", "details": "Le jeton a expiré."}), 401


# Configuration de la connexion à la base de données PostgreSQL
PG_PASSWORD = os.getenv("PG_PASSWORD")  # Mot de passe récupéré depuis les variables d'environnement
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": PG_PASSWORD,
    "host": "127.0.0.1",
    "port": "5432"
}

# Test rapide de connexion à PostgreSQL pour vérifier la validité des paramètres
try:
    test_conn = psycopg2.connect(**DB_CONFIG)
    print("Connexion à PostgreSQL réussie.")
    test_conn.close()
except Exception as e:
    print(f"Erreur de connexion à PostgreSQL : {e}")


# Importation des configurations des modèles et des fonctions liées aux agents et conversations
from models_config_local import MODEL_INFOS
from models_config_enligne import MODELS_ENLIGNE
from agent_principal import poser_question_local, poser_question_enligne
from agent_generation_enligne import choisir_modele_enligne, generer_reponse
from agent_generation_local import charger_modele, MODEL_DIR
from agent_conversation import (
    get_all_conversations_for_user,
    get_conversation_history,
    create_new_conversation,
    rename_conversation,
    delete_conversation,
    get_db_connection,
    save_conversation
)
from agent_importation import upload_document
from agent_pretraitement import run_preprocessing


# Configuration du dossier pour les fichiers uploadés et types de fichiers autorisés
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'csv', 'docx', 'xlsx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Création du dossier s'il n'existe pas
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Cache en mémoire pour les modèles chargés localement
MODELES_CHARGES = {}

# Dictionnaire pour suivre le statut des téléchargements de modèles
DOWNLOAD_STATUS = {}


def allowed_file(filename):
    """
    Vérifie si le fichier a une extension autorisée pour l'upload.
    :param filename: nom du fichier
    :return: True si extension autorisée, False sinon
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== AUTHENTIFICATION ====================

# Route POST /register : inscription d'un nouvel utilisateur
@app.route("/register", methods=["POST"])
def register():
    """
    Enregistre un nouvel utilisateur avec username, email, et mot de passe.
    Le mot de passe est haché avant insertion dans la base.
    """
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    # Validation des champs obligatoires
    if not all([username, email, password]):
        return jsonify({"error": "Champs manquants"}), 400

    # Hashage du mot de passe
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    conn = None  # Initialisation connexion à la BDD
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Vérifier que l'email n'existe pas déjà
            cur.execute("SELECT * FROM utilisateur WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({"error": "Email déjà utilisé"}), 400

            # Insertion de l'utilisateur dans la table
            cur.execute("""
                INSERT INTO utilisateur (username, email, password_hash, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (username, email, password_hash))
            conn.commit()

        return jsonify({"message": "Utilisateur enregistré avec succès."}), 201
    except Exception as e:
        print(f"Erreur lors de l'enregistrement : {e}")
        if conn: conn.rollback()  # Annuler la transaction en cas d'erreur
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        if conn: conn.close()  # Fermer la connexion


# Route POST /login : connexion utilisateur
@app.route("/login", methods=["POST"])
def login():
    """
    Authentifie un utilisateur par email et mot de passe.
    Si succès, renvoie un JWT et les infos utilisateur.
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "Champs manquants"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Récupérer l'utilisateur par email
            cur.execute("SELECT * FROM utilisateur WHERE email = %s", (email,))
            user = cur.fetchone()

            # Vérifier le mot de passe avec bcrypt
            if user and bcrypt.check_password_hash(user["password_hash"], password):
                # Créer un JWT avec l'ID utilisateur (converti en chaîne)
                access_token = create_access_token(identity=str(user["id"]))
                print(f"User {user['id']} logged in. Token created.")
                return jsonify({
                    "message": "Connexion réussie",
                    "access_token": access_token,
                    "user": {
                        "id": user["id"],
                        "username": user["username"],
                        "email": user["email"],
                        "created_at": user["created_at"]
                    }
                }), 200
            else:
                return jsonify({"error": "Email ou mot de passe invalide"}), 401
    except Exception as e:
        print(e)
        return jsonify({"error": "Erreur serveur"}), 500
    finally:
        if conn: conn.close()


# ==================== CHAT ====================

# Route POST /chat : génération de réponse à une question
@app.route("/chat", methods=["POST"])
@jwt_required()  # Nécessite un token JWT valide
def chat():
    """
    Reçoit une question, le type d'agent (local/enligne), le nom du modèle et l'ID de conversation.
    Vérifie que la conversation appartient bien à l'utilisateur,
    appelle l'agent local ou en ligne pour générer la réponse,
    puis sauvegarde la conversation en base.
    """
    data = request.get_json()
    question = data.get("question")
    agent_type = data.get("agent_type")
    model_name = data.get("model_name")
    conversation_id_from_frontend = data.get("conversation_id")  # Valeur originale reçue

    user_id = get_jwt_identity()  # ID utilisateur extrait du token JWT (type string)

    print(f"Chat request received: question='{question}', agent_type='{agent_type}', model_name='{model_name}', conversation_id (from frontend): '{conversation_id_from_frontend}'")
    print(f"User ID from JWT: '{user_id}'")

    # Vérification des champs requis
    if not all([question, agent_type, model_name, conversation_id_from_frontend is not None]):
        print("Missing fields in chat request.")
        return jsonify({"error": "Champs manquants"}), 400

    try:
        # Conversion des IDs en int
        conversation_id = int(conversation_id_from_frontend)
        user_id_int = int(user_id)
        print(f"Converted conversation_id to int: {conversation_id}, Converted user_id to int: {user_id_int}")

        # Vérifier que la conversation appartient bien à l'utilisateur connecté
        conn_check = None
        try:
            conn_check = get_db_connection()
            with conn_check.cursor() as cur_check:
                cur_check.execute("SELECT user_id FROM conversations WHERE id = %s", (conversation_id,))
                conv_owner_id = cur_check.fetchone()
                if not conv_owner_id or conv_owner_id[0] != user_id_int:
                    print(f"Unauthorized access: conv_owner_id={conv_owner_id}, user_id_int={user_id_int}")
                    return jsonify({"error": "Accès non autorisé à la conversation"}), 403
        finally:
            if conn_check: conn_check.close()

        # En fonction du type d'agent, appeler la fonction correspondante
        if agent_type == "local":
            # Vérifier que le modèle local existe
            if model_name not in MODEL_INFOS:
                print(f"Local model not recognized: {model_name}")
                return jsonify({"error": "Modèle local non reconnu"}), 400

            # Charger le modèle si ce n'est pas déjà fait
            if model_name not in MODELES_CHARGES:
                chemin = MODEL_INFOS[model_name]["chemin"]
                MODELES_CHARGES[model_name] = charger_modele(chemin)

            llm = MODELES_CHARGES[model_name]
            print(f"Calling poser_question_local with conv_id: {conversation_id}")
            reponse = poser_question_local(user_id_int, question, llm, conversation_id)

        elif agent_type == "enligne":
            # Pour agent en ligne, vérifier que l'URL API est reconnue dans la config MODELS_ENLIGNE
            actual_api_url_to_pass = None

            print("=== MODELS_ENLIGNE disponibles ===")
            for key, val in MODELS_ENLIGNE.items():
                print(f"- nom: {val['nom']}, model_id: {val.get('model_id')}, api_url: {val['api_url']}")

                if val["api_url"] == model_name:
                    actual_api_url_to_pass = val["api_url"]
                    break

            if not actual_api_url_to_pass:
                print(f"Online model URL not recognized: {model_name}")
                return jsonify({"error": "Modèle en ligne non reconnu"}), 400

            print(f"DEBUG: model_name (api_url from frontend): {model_name}")
            print(f"DEBUG: Using actual_api_url_to_pass: {actual_api_url_to_pass}")
            print(f"DEBUG: Calling poser_question_enligne with user_id_int={user_id_int}, question='{question}', conversation_id={conversation_id}, api_url_for_online_agent='{actual_api_url_to_pass}'")

            # Appeler l'agent en ligne avec l'URL validée
            reponse = poser_question_enligne(user_id_int, question, conversation_id, actual_api_url_to_pass)

        else:
            print(f"Invalid agent type: {agent_type}")
            return jsonify({"error": "Type d'agent invalide"}), 400

        # Sauvegarder la question et la réponse dans la conversation
        print(f"Saving conversation: user_id={user_id_int}, conv_id={conversation_id}")
        save_conversation(user_id_int, conversation_id, question, reponse)

        return jsonify({"reponse": reponse})

    except ValueError as ve:
        # Erreur lors de la conversion d'ID en int
        print(f"ValueError: {ve} - input for int() was problematic.")
        return jsonify({"error": "ID de conversation invalide."}), 400

    except Exception as e:
        # Gestion générique des autres erreurs
        import traceback
        traceback.print_exc()
        print(f"Erreur lors du chat (catch principal) : {e}")
        return jsonify({"error": str(e)}), 500









BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Chemin vers rag_multiagents/agents
MODEL_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "models"))  # Chemin vers rag_multiagents/models

# Dictionnaire global pour suivre le statut des téléchargements de modèles
# Clé = nom du modèle, valeur = dict avec status (ex: downloading, completed) et cancel_event (threading.Event)
DOWNLOAD_STATUS = {}

# ==================== LISTE DES MODÈLES ====================

# === ROUTE: Récupérer la liste des modèles disponibles, avec leur statut
@app.route('/models', methods=['GET'])
def get_models():
    """
    Récupère la liste des modèles disponibles.
    Selon le type d'agent demandé (local ou enligne), renvoie la liste des modèles
    avec leur statut de téléchargement.
    """
    agent_type = request.args.get('agent_type')

    if agent_type == "local":
        models = []
        for name, info in MODEL_INFOS.items():
            filename = info["filename"]
            model_path = os.path.join(MODEL_DIR, filename)
            downloaded = os.path.exists(model_path)

            status_info = DOWNLOAD_STATUS.get(name, {})
            current_status = status_info.get('status')
            if downloaded and current_status not in ["downloading", "cancelled", "failed"]:
                current_status = "completed"
            elif not downloaded and not current_status:
                current_status = "not_downloaded"

            models.append({
                "name": name,
                "value": name,
                "downloaded": downloaded,
                "status": current_status
            })
        return jsonify(models)

    elif agent_type == "enligne":
        models = []
        for id_, model in MODELS_ENLIGNE.items():
            models.append({
                "name": model["nom"],
                "value": model["api_url"],
                "api_url": model["api_url"],
                "status": "available",
                "downloaded": True
            })

        return jsonify(models)

    else:
        return jsonify({"error": "Type d'agent invalide"}), 400


# === ROUTE: Vérifier si un modèle est téléchargé
@app.route('/check_model_downloaded/<model_name>', methods=['GET'])
@jwt_required()
def check_model_downloaded_route(model_name):
    """
    Vérifie le statut de téléchargement d'un modèle donné.
    Renvoie si le modèle est téléchargé et son état actuel.
    """
    if model_name not in MODEL_INFOS:
        return jsonify({"error": "Modèle non reconnu"}), 404

    filename = MODEL_INFOS[model_name]["filename"]
    model_path = os.path.join(MODEL_DIR, filename)
    downloaded = os.path.exists(model_path)

    status_info = DOWNLOAD_STATUS.get(model_name, {})
    current_status = status_info.get('status')

    if downloaded and current_status not in ["downloading", "cancelled", "failed"]:
        current_status = "completed"
    elif not downloaded and not current_status:
        current_status = "not_downloaded"

    return jsonify({
        "model_name": model_name,
        "downloaded": downloaded,
        "status": current_status
    }), 200


# === ROUTE: Lancer le téléchargement d'un modèle
@app.route('/download_model/<model_name>', methods=['POST'])
@jwt_required()
def download_model_route(model_name):
    """
    Démarre le téléchargement en arrière-plan d'un modèle donné.
    Si le modèle est déjà téléchargé ou en cours, renvoie un message approprié.
    """
    if model_name not in MODEL_INFOS:
        return jsonify({"error": "Modèle non reconnu"}), 404

    filename = MODEL_INFOS[model_name]["filename"]
    url = MODEL_INFOS[model_name]["url"]
    model_path = os.path.join(MODEL_DIR, filename)

    if os.path.exists(model_path):
        return jsonify({"message": f"Modèle '{model_name}' déjà téléchargé."}), 200

    if DOWNLOAD_STATUS.get(model_name, {}).get("status") == "downloading":
        return jsonify({"message": f"Le téléchargement du modèle '{model_name}' est déjà en cours."}), 202

    cancel_event = threading.Event()
    DOWNLOAD_STATUS[model_name] = {
        "status": "downloading",
        "cancel_event": cancel_event
    }

    thread = threading.Thread(target=download_model_background, args=(model_name, url, filename, cancel_event))
    thread.start()

    return jsonify({"message": f"Téléchargement du modèle '{model_name}' lancé."}), 202


# === ROUTE: Annuler un téléchargement en cours
@app.route('/cancel_download/<model_name>', methods=['POST'])
@jwt_required()
def cancel_download_route(model_name):
    """
    Annule un téléchargement en cours pour un modèle donné.
    Met à jour le statut et signale l'annulation via l'Event.
    """
    if model_name not in DOWNLOAD_STATUS:
        return jsonify({"error": f"Aucun téléchargement en cours pour '{model_name}'."}), 404

    status_entry = DOWNLOAD_STATUS[model_name]
    if status_entry["status"] == "downloading":
        status_entry["cancel_event"].set()  # Signal d'annulation
        status_entry["status"] = "cancelled"
        return jsonify({"message": f"Téléchargement de '{model_name}' annulé."}), 202
    elif status_entry["status"] == "completed":
        return jsonify({"message": f"Le modèle '{model_name}' est déjà téléchargé."}), 200
    else:
        return jsonify({"message": f"État du modèle '{model_name}' : {status_entry['status']}"}), 400


# === Fonction: Télécharger un modèle en arrière-plan
def download_model_background(model_name, url, filename, cancel_event):
    """
    Télécharge un modèle depuis une URL en écrivant le contenu dans un fichier local.
    Permet l'annulation en vérifiant périodiquement le cancel_event.
    Met à jour le dictionnaire DOWNLOAD_STATUS avec le statut courant.
    """
    import requests

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        os.makedirs(MODEL_DIR, exist_ok=True)
        filepath = os.path.join(MODEL_DIR, filename)

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if cancel_event.is_set():
                    print(f"Téléchargement de '{model_name}' annulé.")
                    f.close()
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    DOWNLOAD_STATUS[model_name]["status"] = "cancelled"
                    return
                if chunk:
                    f.write(chunk)

        DOWNLOAD_STATUS[model_name]["status"] = "completed"
        print(f"Téléchargement de '{model_name}' terminé.")
    except Exception as e:
        print(f"Erreur lors du téléchargement de '{model_name}': {str(e)}")
        DOWNLOAD_STATUS[model_name]["status"] = "failed"


# ==================== CONVERSATIONS ====================

# === ROUTE: Récupérer toutes les conversations d'un utilisateur
@app.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations_route():
    """
    Renvoie la liste des conversations (avec titres) pour l'utilisateur authentifié.
    """
    print("Appel reçu /conversations")
    user_id = get_jwt_identity()  # user_id est une chaîne
    print(f"User ID from JWT (string): {user_id} (for /conversations)")

    try:
        user_id_int = int(user_id)
        conversations_with_titles = get_all_conversations_for_user(user_id_int)
        print("Conversations récupérées :", conversations_with_titles)
        return jsonify(conversations_with_titles)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Erreur générale dans la route /conversations (après vérification JWT) : {e}")
        return jsonify({"error": "Erreur lors de la récupération des conversations.", "details": str(e)}), 500


# === ROUTE: Récupérer l'historique d'une conversation spécifique
@app.route('/conversation_history/<int:conversation_id>', methods=['GET'])
@jwt_required()
def get_messages_for_conversation_route(conversation_id):
    """
    Récupère l'historique complet d'une conversation pour l'utilisateur connecté.
    Renvoie une liste alternant messages de l'utilisateur et réponses du bot.
    """
    user_id = get_jwt_identity()
    print(f"Received call /conversation_history for conversation_id: {conversation_id}")
    print(f"User ID from JWT (string) for history: {user_id}")

    try:
        user_id_int = int(user_id)
        history_raw = get_conversation_history(user_id_int, conversation_id)
        print(f"Raw history fetched for conv {conversation_id}: {history_raw}")

        messages_formatted = []
        for entry in history_raw:
            messages_formatted.append({"from": "user", "text": entry['user_message']})
            messages_formatted.append({"from": "bot", "text": entry['bot_response']})

        print(f"Formatted messages for conv {conversation_id}: {messages_formatted}")
        return jsonify(messages_formatted)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Erreur historique : {e}")
        return jsonify({"error": "Erreur lors de l'historique."}), 500


# === ROUTE: Créer une nouvelle conversation
@app.route('/new_conversation', methods=['POST'])
@jwt_required()
def create_new_conversation_route():
    """
    Crée une nouvelle conversation pour l'utilisateur connecté.
    Renvoie l'id et un titre par défaut de la conversation créée.
    """
    user_id = get_jwt_identity()
    print(f"User ID from JWT (string): {user_id} (for /new_conversation)")
    try:
        user_id_int = int(user_id)
        new_conv_id = create_new_conversation(user_id_int)
        if new_conv_id:
            return jsonify({"conversation_id": new_conv_id, "title": "Nouvelle Conversation"}), 201
        return jsonify({"error": "Impossible de créer la conversation."}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Erreur création : {e}")
        return jsonify({"error": "Erreur serveur."}), 500


# === ROUTE: Renommer une conversation existante
@app.route('/rename_conversation/<int:conversation_id>', methods=['PUT'])
@jwt_required()
def rename_conversation_route(conversation_id):
    """
    Renomme la conversation spécifiée si elle appartient à l'utilisateur.
    Nécessite un JSON avec "new_title".
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    new_title = data.get("new_title")
    if not new_title:
        return jsonify({"error": "Nouveau titre manquant."}), 400

    try:
        user_id_int = int(user_id)
        success = rename_conversation(conversation_id, new_title, user_id_int)
        if success:
            return jsonify({"message": "Renommée avec succès."}), 200
        return jsonify({"error": "Échec du renommage (conversation introuvable ou non autorisée)."}), 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Erreur renommage : {e}")
        return jsonify({"error": "Erreur serveur."}), 500


# === ROUTE: Supprimer une conversation
@app.route('/delete_conversation/<int:conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation_route(conversation_id):
    """
    Supprime la conversation spécifiée si elle appartient à l'utilisateur.
    """
    user_id = get_jwt_identity()

    try:
        user_id_int = int(user_id)
        success = delete_conversation(conversation_id, user_id_int)
        if success:
            return jsonify({"message": "Supprimée avec succès."}), 200
        return jsonify({"error": "Échec de la suppression (conversation introuvable ou non autorisée)."}), 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Erreur suppression : {e}")
        return jsonify({"error": "Erreur serveur."}), 500


# ==================== DOCUMENTS ====================

# === ROUTE: Upload de document(s) pour une conversation donnée
@app.route('/upload_document/<int:conversation_id>', methods=['POST'])
@jwt_required()
def upload_document_route(conversation_id):
    """
    Permet à l'utilisateur connecté d'uploader un ou plusieurs documents
    associés à une conversation. Les fichiers sont temporairement enregistrés,
    puis traités et supprimés.
    """
    user_id = get_jwt_identity()
    user_id = int(user_id)

    print(f"Received upload request for conversation_id: {conversation_id}, user_id: {user_id}")

    if 'file' not in request.files:
        print("Error: No 'file' part in request.files")
        return jsonify({'error': 'Aucun fichier trouvé'}), 400

    files = request.files.getlist('file')
    if not files or not any(f.filename for f in files):
        print("Error: No files selected or filenames empty")
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    uploaded_count = 0
    errors = []

    try:
        for file in files:
            print(f"Processing file: {file.filename}")
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                print(f"Saving file temporarily to: {filepath}")
                try:
                    file.save(filepath)
                    print(f"Calling upload_document with filepath: {filepath}, conv_id: {conversation_id}, user_id: {user_id}")
                    upload_document(filepath, conversation_id, user_id)
                    os.remove(filepath)
                    print(f"Successfully processed and removed {filename}")
                    uploaded_count += 1
                except Exception as e:
                    errors.append(f"Erreur fichier {filename}: {str(e)}")
                    print(f"Inner exception during file processing: {e}")
                    import traceback; traceback.print_exc()
            else:
                errors.append(f"Fichier non autorisé : {file.filename}")
                print(f"File not allowed: {file.filename}")

        if uploaded_count > 0:
            print(f"Upload avec succes de {uploaded_count} documents. preprocessing pour conv_id: {conversation_id}")
            run_preprocessing(conversation_id)
            return jsonify({'message': f'{uploaded_count} document(s) traité(s)', 'errors': errors}), 200

        print(f"No valid documents uploaded. Errors: {errors}")
        return jsonify({'error': 'Aucun document valide', 'errors': errors}), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Erreur upload (catch principal) : {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


# ==================== MAIN ====================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
